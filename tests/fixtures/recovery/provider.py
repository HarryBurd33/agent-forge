#!/usr/bin/env python3
"""Local outbox fixture. Public CLI exposes send and lookup."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

STATE = Path(os.environ['AGENT_FORGE_TEST_PROVIDER_STATE']).resolve()
CASES = ('lost_ack', 'conflict', 'unknown', 'not_committed')
SCHEMA = '''
CREATE TABLE operations (key TEXT PRIMARY KEY, identity TEXT NOT NULL, state TEXT NOT NULL, receipt TEXT);
CREATE TABLE calls (id INTEGER PRIMARY KEY, at TEXT NOT NULL, command TEXT NOT NULL,
    arguments TEXT NOT NULL, outcome TEXT NOT NULL);
CREATE TABLE effects (id INTEGER PRIMARY KEY, at TEXT NOT NULL, key TEXT NOT NULL UNIQUE,
    identity TEXT NOT NULL, payload TEXT NOT NULL, origin TEXT NOT NULL, receipt TEXT NOT NULL);
'''


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def make_identity(key, action, target, payload, source_version):
    return dict(key=key, action=action, target=target,
                payload_sha256=hashlib.sha256(canonical(payload).encode('utf-8')).hexdigest(),
                source_version=source_version)


def parse_payload(value):
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError('duplicate payload key')
            result[key] = item
        return result

    payload = json.loads(value, object_pairs_hook=unique)
    if type(payload) is not dict or set(payload) != {'total'} or type(payload['total']) is not int:
        raise ValueError('payload must be an object containing exactly one integer total')
    return payload


def current(db, key):
    row = db.execute('SELECT identity, state, receipt FROM operations WHERE key = ?', (key,)).fetchone()
    if row is None:
        return {'status': 'unknown', 'key': key}
    identity, status, receipt = row
    result = dict(status=status, **json.loads(identity))
    if receipt is not None:
        result['receipt'] = receipt
    return result


def put_effect(db, identity, payload, origin):
    key = identity['key']
    receipt = 'local-' + hashlib.sha256(canonical(identity).encode('utf-8')).hexdigest()[:24]
    db.execute('INSERT INTO effects(at,key,identity,payload,origin,receipt) VALUES(?,?,?,?,?,?)',
               (timestamp(), key, canonical(identity), canonical(payload), origin, receipt))
    db.execute('INSERT OR REPLACE INTO operations VALUES(?,?,?,?)',
               (key, canonical(identity), 'committed', receipt))
    return dict(status='committed', **identity, receipt=receipt)


def record(db, command, arguments, outcome):
    db.execute('INSERT INTO calls(at,command,arguments,outcome) VALUES(?,?,?,?)',
               (timestamp(), command, canonical(arguments), outcome))


def emit(result):
    print(canonical(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('lookup').add_argument('--key', required=True)
    send = sub.add_parser('send')
    send.add_argument('--key', required=True)
    send.add_argument('--action', required=True)
    send.add_argument('--target', required=True)
    send.add_argument('--payload-json', required=True)
    send.add_argument('--source-version', required=True)
    args = parser.parse_args()
    path = STATE / (args.case + '.sqlite3')
    if not path.is_file():
        emit({'status': 'unavailable', 'reason': 'case state is not initialized'})
        return 69
    db = sqlite3.connect(path, timeout=5, isolation_level=None)
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        code = 0
        log_args = {'key': args.key}
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}', args.key):
            result, code = {'status': 'invalid', 'reason': 'invalid operation key'}, 64
        elif args.command == 'lookup':
            result = current(db, args.key)
        else:
            try:
                if args.action != 'deliver' or args.target not in ('local-outbox-blue', 'local-outbox-red'):
                    raise ValueError('unsupported local action or target')
                if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}', args.source_version):
                    raise ValueError('invalid source version')
                payload = parse_payload(args.payload_json)
            except ValueError as error:
                result, code = {'status': 'invalid', 'reason': str(error)}, 64
            else:
                identity = make_identity(args.key, args.action, args.target, payload, args.source_version)
                log_args = identity
                prior = current(db, args.key)
                if prior['status'] != 'unknown' and any(prior[field] != value for field, value in identity.items()):
                    result, code = {'status': 'identity_conflict', 'existing': prior}, 73
                elif prior['status'] == 'committed':
                    result = prior
                else:
                    result = put_effect(db, identity, payload, 'send')
                    if args.case == 'lost_ack':
                        code = 75
        record(db, args.command, log_args, 'committed_ack_lost' if code == 75 else result['status'])
        db.commit()
    finally:
        db.close()
    if code == 75:
        print('Acknowledgement unavailable. Outcome must be reconciled.', file=sys.stderr)
    else:
        emit(result)
    return code


if __name__ == '__main__':
    sys.exit(main())
