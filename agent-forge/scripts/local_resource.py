#!/usr/bin/env python3
"""Fence ownership and apply idempotent integer updates to one local SQLite resource."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import sys
import time


MAX_INTEGER = (1 << 53) - 1
MAX_TTL_MS = 86_400_000
BUSY_TIMEOUT_SECONDS = 5
SCHEMA = (
    """CREATE TABLE IF NOT EXISTS resources (
        resource TEXT PRIMARY KEY,
        owner TEXT,
        token INTEGER NOT NULL CHECK (token BETWEEN 1 AND 9007199254740991),
        expires_at_ms INTEGER,
        value INTEGER NOT NULL CHECK (value BETWEEN -9007199254740991 AND 9007199254740991),
        CHECK ((owner IS NULL) = (expires_at_ms IS NULL))
    )""",
    """CREATE TABLE IF NOT EXISTS operations (
        resource TEXT NOT NULL REFERENCES resources(resource),
        operation_key TEXT NOT NULL,
        delta INTEGER NOT NULL,
        value INTEGER NOT NULL,
        token INTEGER NOT NULL,
        PRIMARY KEY (resource, operation_key)
    )""",
)
FIELDS = {
    "claim": ("resource", "owner", "ttl_ms"),
    "release": ("resource", "owner", "token"),
    "apply": ("resource", "owner", "token", "operation_key", "delta"),
    "lookup": ("resource", "operation_key", "delta"),
    "read": ("resource",),
}
WRITE_ACTIONS = {"claim", "release", "apply"}


def validate(action, request):
    if not isinstance(request, dict) or set(request) != set(FIELDS[action]):
        raise ValueError(f"{action} requires exactly {', '.join(FIELDS[action])}")
    for key in ("resource", "owner", "operation_key"):
        if key in request:
            value = request[key]
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ValueError(f"{key} must be a nonempty string of at most 256 characters")
    for key, low, high in (
        ("ttl_ms", 1, MAX_TTL_MS),
        ("token", 1, MAX_INTEGER),
        ("delta", -MAX_INTEGER, MAX_INTEGER),
    ):
        if key in request:
            value = request[key]
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{key} must be an integer from {low} to {high}")


def clock_ms():
    return time.time_ns() // 1_000_000


@contextmanager
def database(path, *, writable):
    uri = path.resolve().as_uri() + ("?mode=rwc" if writable else "?mode=ro")
    db = sqlite3.connect(uri, uri=True, timeout=BUSY_TIMEOUT_SECONDS, isolation_level=None)
    try:
        db.row_factory = sqlite3.Row
        if writable:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("BEGIN IMMEDIATE")
            for statement in SCHEMA:
                db.execute(statement)
        yield db
        if writable:
            db.execute("COMMIT")
    finally:
        db.close()


def claim(db, resource, owner, ttl_ms):
    now = clock_ms()
    previous = db.execute(
        "SELECT token, expires_at_ms FROM resources WHERE resource = ?", (resource,),
    ).fetchone()
    if previous is None:
        token = 1
        db.execute(
            "INSERT INTO resources VALUES (?, ?, ?, ?, 0)",
            (resource, owner, token, now + ttl_ms),
        )
    else:
        expires_at = previous["expires_at_ms"]
        if expires_at is not None and expires_at > now:
            return {"status": "busy"}
        token = previous["token"] + 1
        if token > MAX_INTEGER:
            raise ValueError("Resource fence exhausted")
        db.execute(
            "UPDATE resources SET owner = ?, token = ?, expires_at_ms = ? WHERE resource = ?",
            (owner, token, now + ttl_ms, resource),
        )
    return {"status": "claimed", "token": token, "expires_at_ms": now + ttl_ms}


def active_lease(db, resource, owner, token):
    return db.execute(
        """SELECT value FROM resources
           WHERE resource = ? AND owner = ? AND token = ? AND expires_at_ms > ?""",
        (resource, owner, token, clock_ms()),
    ).fetchone()


def release(db, resource, owner, token):
    if active_lease(db, resource, owner, token) is None:
        return {"status": "stale"}
    db.execute(
        "UPDATE resources SET owner = NULL, expires_at_ms = NULL WHERE resource = ?",
        (resource,),
    )
    return {"status": "released"}


def read_operation(db, resource, operation_key, delta):
    operation = db.execute(
        "SELECT delta, value, token FROM operations WHERE resource = ? AND operation_key = ?",
        (resource, operation_key),
    ).fetchone()
    if operation is None:
        return {"status": "unknown"}
    if operation["delta"] != delta:
        return {"status": "conflict"}
    return {"status": "committed", "value": operation["value"], "token": operation["token"]}


def apply(db, resource, owner, token, operation_key, delta):
    # The lease check and both writes run while this connection holds the SQLite write lock.
    lease = active_lease(db, resource, owner, token)
    if lease is None:
        return {"status": "stale"}
    previous = read_operation(db, resource, operation_key, delta)
    if previous["status"] == "conflict":
        return previous
    if previous["status"] == "committed":
        return {**previous, "status": "replayed"}

    value = lease["value"] + delta
    if not -MAX_INTEGER <= value <= MAX_INTEGER:
        raise ValueError("Resource value would exceed the supported integer range")
    db.execute("UPDATE resources SET value = ? WHERE resource = ?", (value, resource))
    db.execute(
        "INSERT INTO operations VALUES (?, ?, ?, ?, ?)",
        (resource, operation_key, delta, value, token),
    )
    return {"status": "committed", "value": value, "token": token}


def read_resource(db, resource):
    row = db.execute(
        "SELECT value, token, owner, expires_at_ms FROM resources WHERE resource = ?",
        (resource,),
    ).fetchone()
    return {"status": "unknown"} if row is None else {"status": "present", **dict(row)}


OPERATIONS = {
    "claim": claim, "release": release, "apply": apply,
    "lookup": read_operation, "read": read_resource,
}


def execute(path, action, request):
    validate(action, request)
    if action != "claim" and not path.exists():
        return {"status": "stale" if action in WRITE_ACTIONS else "unknown"}
    with database(path, writable=action in WRITE_ACTIONS) as db:
        return OPERATIONS[action](db, **request)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("action", choices=OPERATIONS)
    args = parser.parse_args(argv)
    try:
        response = execute(args.db, args.action, json.load(sys.stdin))
        code = 0
    except (ValueError, sqlite3.Error, OSError) as error:
        response = {"status": "error", "error": str(error)}
        code = 2
    print(json.dumps(response))
    return code


if __name__ == "__main__":
    sys.exit(main())
