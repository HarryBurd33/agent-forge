#!/usr/bin/env python3
"""Seed, search and structurally audit Agent Forge projects. No task execution."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
from urllib.parse import urlsplit


SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXTERNAL_SCHEMES = {"https", "drive", "notion", "page", "s3"}
SKIP_DIRS = {".git", ".checkpoint", ".private", ".build-private", "__pycache__"}
WARNING = "Structural audit only: does not establish task quality, authority, scheduler registration, external access or absence of all secrets."


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and all(text(x) for x in value)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def number(value, minimum=0, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > minimum if positive else value >= minimum)


def read_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, parse_constant=lambda value: (_ for _ in ()).throw(Invalid("nonfinite JSON number: " + value)))


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def credential_path(parts):
    for part in parts:
        lower = part.lower()
        if lower in {".env", ".aws", ".ssh", "credentials", "credentials.json", "auth.json", "id_rsa", "id_ed25519"}:
            return True
        if lower.startswith(".env.") or lower.endswith((".pem", ".key", ".p12", ".pfx")):
            return True
    return False


def local_path(root, value, must_exist=True):
    require(text(value), "location must be nonempty text")
    pure = PurePosixPath(value)
    require(not pure.is_absolute() and ".." not in pure.parts and "\\" not in value and ":" not in value,
            "unsafe local path: " + value)
    require(pure.parts and value not in (".", ""), "file path required")
    require(not credential_path(pure.parts), "credential-like path excluded: " + value)
    path = root.joinpath(*pure.parts)
    require(path.resolve().is_relative_to(root.resolve()), "path escapes project: " + value)
    if must_exist:
        require(path.is_file(), "missing resource/evidence file: " + value)
    return path


def location(root, value, must_exist=True):
    require(text(value), "location must be nonempty text")
    if "://" in value:
        uri = urlsplit(value)
        require(uri.scheme in EXTERNAL_SCHEMES and bool(uri.netloc), "unsupported external URI: " + value)
        require(uri.username is None and uri.password is None and not uri.query and not uri.fragment,
                "external references must omit credentials, query and fragment: " + value)
        return None
    return local_path(root, value, must_exist)


def object_fields(value, fields, label):
    require(isinstance(value, dict), label + " must be an object")
    missing = set(fields) - value.keys()
    require(not missing, label + " missing fields: " + ", ".join(sorted(missing)))


def init(destination, project_id):
    require(bool(SLUG.fullmatch(project_id)), "project-id must be lowercase hyphenated text")
    require(".." not in destination.parts, "destination traversal is forbidden")
    require(not destination.exists() and not destination.is_symlink(), "destination already exists; refusing overwrite")
    for ancestor in destination.parents:
        require(not ancestor.is_symlink(), "symlink destination ancestor is forbidden")
    require(destination.parent.is_dir(), "destination parent must already exist")
    templates = Path(__file__).resolve().parents[1] / "templates"
    sources = {"AGENT.md": "AGENT.md", "PLAYBOOK.md": "PLAYBOOK.md", "agent.json": "agent.json", "toolbox-index.json": "toolbox/index.json"}
    contents = {target: (templates / source).read_text(encoding="utf-8").replace("PROJECT_ID", project_id)
                for source, target in sources.items()}
    created = False
    try:
        destination.mkdir()
        created = True
        (destination / "toolbox").mkdir()
        for target, content in contents.items():
            with (destination / target).open("x", encoding="utf-8") as handle:
                handle.write(content)
    except Exception:
        if created:
            shutil.rmtree(destination)
        raise
    return {"ok": True, "project": str(destination.resolve()), "status": "draft", "created": list(contents), "warnings": [WARNING, "Execution mode and authority are unset. No task or job was launched."]}


def load_project(root):
    require(root.is_dir(), "project directory does not exist")
    config = read_json(local_path(root, "agent.json"))
    object_fields(config, ("schema_version", "project_id", "status", "instructions", "playbook", "toolbox", "execution", "bounds", "capabilities", "authority", "retention"), "agent.json")
    require(config["schema_version"] == 1 and type(config["schema_version"]) is int, "unsupported agent schema_version")
    require(text(config["project_id"]) and bool(SLUG.fullmatch(config["project_id"])), "invalid project_id")
    require(config["status"] in ("draft", "ready", "blocked"), "invalid project status")
    for field in ("instructions", "playbook", "toolbox"):
        local_path(root, config[field])
    index = read_json(local_path(root, config["toolbox"]))
    object_fields(index, ("schema_version", "project_id", "resources"), "toolbox index")
    require(type(index["schema_version"]) is int and index["schema_version"] == 1, "unsupported toolbox schema_version")
    require(index["project_id"] == config["project_id"], "project IDs do not match")
    require(isinstance(index["resources"], list), "resources must be an array")
    return config, index


def audit(root, ready=False):
    errors, warnings = [], [WARNING]
    try:
        config, index = load_project(root)
        playbook = local_path(root, config["playbook"]).read_text(encoding="utf-8")
        bounds = config["bounds"]
        object_fields(bounds, ("max_attempts", "max_minutes", "max_depth", "max_concurrency", "max_workers", "max_cost_usd"), "bounds")
        require(integer(bounds["max_attempts"], 1), "max_attempts must be an integer >= 1")
        require(number(bounds["max_minutes"], positive=True), "max_minutes must be positive and finite")
        for field in ("max_depth", "max_concurrency", "max_workers"):
            require(integer(bounds[field]), field + " must be a nonnegative integer")
        require(bounds["max_cost_usd"] is None or number(bounds["max_cost_usd"]), "max_cost_usd must be null or finite nonnegative number")
        if any(bounds[k] == 0 for k in ("max_depth", "max_concurrency", "max_workers")):
            warnings.append("Delegation disabled by an explicit zero bound.")
        execution = config["execution"]
        object_fields(execution, ("mode", "trigger", "timezone", "dependencies", "ordering", "overlap_policy", "retry_policy", "stop_conditions", "notification", "registration"), "execution")
        require(execution["mode"] in (None, "manual", "one_time", "recurring", "event"), "invalid execution mode")
        for field in ("dependencies", "stop_conditions"):
            require(strings(execution[field]), "execution." + field + " must be an array of strings")
        for field in ("ordering", "overlap_policy", "retry_policy"):
            require(text(execution[field]), "execution." + field + " required")
        registration = execution["registration"]
        object_fields(registration, ("provider", "id", "status", "verified_at", "evidence"), "registration")
        require(text(registration["status"]) and strings(registration["evidence"]), "invalid registration metadata")
        for ref in registration["evidence"]:
            location(root, ref)
        if registration["status"] in ("registered", "active", "enabled", "paused"):
            require(all(text(registration[k]) for k in ("provider", "id", "verified_at")) and bool(registration["evidence"]), "claimed registration requires identity, time and evidence")
        capabilities = config["capabilities"]
        object_fields(capabilities, ("required", "optional", "observed", "missing"), "capabilities")
        for key in ("required", "optional", "observed", "missing"):
            require(strings(capabilities[key]), "capabilities." + key + " must be an array of strings")
        authority = config["authority"]
        object_fields(authority, ("source", "allowed", "escalate", "external_actions"), "authority")
        for key in ("allowed", "escalate", "external_actions"):
            require(strings(authority[key]), "authority." + key + " must be an array of strings")
        retention = config["retention"]
        object_fields(retention, ("temporary_dirs", "temporary_days", "durable"), "retention")
        require(strings(retention["temporary_dirs"]) and integer(retention["temporary_days"]) and text(retention["durable"]), "invalid retention")
        temporary = []
        for value in retention["temporary_dirs"]:
            path = local_path(root, value, must_exist=False)
            require(path != root and PurePosixPath(value).parts[0] not in ("outputs", "runs", "toolbox"),
                    "cannot exclude durable resource directories or descendants")
            temporary.append(PurePosixPath(value))
        resources, ids, locations, graph = index["resources"], {}, set(), {}
        for entry in resources:
            object_fields(entry, ("id", "purpose", "kind", "location", "version", "input_contract", "output_contract", "dependencies", "status", "used_by", "validation", "replaces", "reuse_decision"), "resource")
            ident = entry["id"]
            require(text(ident) and bool(SLUG.fullmatch(ident)), "invalid resource id")
            require(ident not in ids, "duplicate resource id: " + ident)
            for key in ("purpose", "kind", "version", "input_contract", "output_contract", "reuse_decision"):
                require(text(entry[key]), ident + ": " + key + " required")
            path = location(root, entry["location"])
            normalized = str(path.resolve()) if path is not None else entry["location"]
            require(normalized not in locations, "duplicate resource location: " + entry["location"])
            locations.add(normalized)
            require(strings(entry["dependencies"]), ident + ": dependencies must be strings")
            require(strings(entry["used_by"]) and bool(entry["used_by"]), ident + ": used_by required")
            for ref in entry["used_by"]:
                require(bool(re.fullmatch(r"(?:step|check)-[a-zA-Z0-9-]+", ref)) and bool(re.search(r"(?<![\w-])" + re.escape(ref) + r"(?![\w-])", playbook)), ident + ": unknown playbook step/check: " + ref)
            require(entry["status"] in ("draft", "validated", "retired"), ident + ": invalid status")
            validation = entry["validation"]
            object_fields(validation, ("method", "evidence"), ident + " validation")
            require(text(validation["method"]) and strings(validation["evidence"]), ident + ": invalid validation")
            if entry["status"] == "validated":
                require(bool(validation["evidence"]), ident + ": validated resource needs evidence")
            for ref in validation["evidence"]:
                location(root, ref)
            bindings = validation.get("bindings", [])
            require(isinstance(bindings, list), ident + ": validation.bindings must be an array")
            seen_bindings = set()
            evidence_paths = set()
            for ref in validation["evidence"]:
                evidence_path = location(root, ref)
                if evidence_path is not None:
                    evidence_paths.add(str(evidence_path.resolve()))
            for binding in bindings:
                object_fields(binding, ("role", "location", "sha256"), ident + " freshness binding")
                role, bound_location, expected = binding["role"], binding["location"], binding["sha256"]
                require(role in ("source", "evidence"), ident + ": binding role must be source or evidence")
                require(text(expected) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", expected)),
                        ident + ": binding sha256 must be 64 hexadecimal characters")
                bound_path = local_path(root, bound_location)
                normalized = str(bound_path.resolve())
                key = (role, normalized)
                require(key not in seen_bindings, ident + ": duplicate freshness binding: " + bound_location)
                seen_bindings.add(key)
                if role == "evidence":
                    require(normalized in evidence_paths,
                            ident + ": evidence binding must appear in validation.evidence: " + bound_location)
                actual = file_sha256(bound_path)
                require(actual.casefold() == expected.casefold(),
                        ident + ": stale " + role + " binding " + bound_location
                        + " (expected sha256 " + expected.casefold() + ", observed " + actual + ")")
            require(entry["replaces"] is None or text(entry["replaces"]), ident + ": replaces must be null or resource ID")
            ids[ident] = entry
            graph[ident] = entry["dependencies"]
        for ident, entry in ids.items():
            for dependency in entry["dependencies"]:
                require(dependency in ids, ident + ": missing dependency: " + dependency)
            if entry["replaces"] is not None:
                require(entry["replaces"] in ids and entry["replaces"] != ident, ident + ": missing or self replacement")
        visited, active = set(), set()
        def visit(ident):
            require(ident not in active, "resource dependency cycle at " + ident)
            if ident in visited:
                return
            active.add(ident)
            for dependency in graph[ident]:
                visit(dependency)
            active.remove(ident)
            visited.add(ident)
        for ident in graph:
            visit(ident)
        for path in root.rglob("*"):
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if any(part in SKIP_DIRS for part in relative.parts) or any(relative == p or p in relative.parents for p in temporary):
                continue
            if path.is_dir() and not path.is_symlink():
                continue
            if credential_path(relative.parts):
                errors.append("credential-like file must be kept outside project: " + str(relative))
                continue
            if path.is_symlink() and not path.resolve().is_relative_to(root.resolve()):
                errors.append("symlink escapes project: " + str(relative))
            elif path.is_file() and str(path.resolve()) not in locations:
                errors.append("unindexed durable file: " + str(relative))
        for field in ("instructions", "playbook", "toolbox"):
            require(str(local_path(root, config[field]).resolve()) in locations, "required artifact is not indexed: " + field)
        require(str((root / "agent.json").resolve()) in locations, "agent.json must be indexed")
        readiness = []
        if config["status"] != "ready":
            readiness.append("project status is not ready")
        if execution["mode"] is None:
            readiness.append("execution mode must be explicitly established")
        if not text(authority["source"]) or not authority["allowed"]:
            readiness.append("current authority source and allowed scope required")
        observed_names = {item.split(":", 1)[0].strip() for item in capabilities["observed"]}
        required_capabilities = set(capabilities["required"])
        optional_capabilities = set(capabilities["optional"])
        missing_capabilities = set(capabilities["missing"])
        missing_required = missing_capabilities & required_capabilities
        undeclared_missing = missing_capabilities - required_capabilities - optional_capabilities
        if missing_required or undeclared_missing or not required_capabilities.issubset(observed_names):
            readiness.append("required capabilities need observations and no unresolved missing capabilities")
        if missing_capabilities & optional_capabilities:
            warnings.append("Optional capabilities unavailable: " + ", ".join(sorted(missing_capabilities & optional_capabilities)))
        if "REPLACE" in playbook or "PROJECT_ID" in playbook:
            readiness.append("playbook contains draft placeholders")
        if not re.search(r"\|\s*check-[\w-]+\s*\|\s*[^|\n]+\|\s*[^|\n]+\|\s*[^|\n]+\|", playbook):
            readiness.append("playbook needs outcome checks with methods and evidence")
        required_locations = {str(local_path(root, config[f]).resolve()) for f in ("instructions", "playbook", "toolbox")} | {str((root / "agent.json").resolve())}
        if any(entry["status"] != "validated" for entry in resources
               if location(root, entry["location"]) is not None
               and str(location(root, entry["location"]).resolve()) in required_locations):
            readiness.append("required seed resources must be validated with evidence")
        if execution["mode"] in ("one_time", "recurring", "event"):
            if not text(execution["trigger"]) or not text(execution["notification"]) or not execution["stop_conditions"]:
                readiness.append("automation trigger, notification and stop conditions required")
            if execution["mode"] != "event" and not text(execution["timezone"]):
                readiness.append("time-based automation requires explicit timezone")
        if ready:
            errors.extend(readiness)
        else:
            warnings.extend(readiness)
        warnings.append("External references were not fetched; registered statuses require independent host readback.")
    except (Invalid, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def find(root, query):
    require(text(query), "query must be nonempty")
    _, index = load_project(root)
    tokens = query.casefold().split()
    matches = []
    for entry in index["resources"]:
        require(isinstance(entry, dict), "resource must be an object")
        haystack = " ".join(str(entry.get(k, "")) for k in ("id", "purpose", "kind", "input_contract", "output_contract", "location")).casefold()
        if all(token in haystack for token in tokens):
            matches.append(entry)
    return {"ok": True, "query": query, "matches": matches}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init", help="Create a new draft; refuse existing destination")
    init_parser.add_argument("project", type=Path)
    init_parser.add_argument("--project-id", required=True)
    find_parser = commands.add_parser("find", help="Search indexed resource metadata")
    find_parser.add_argument("project", type=Path)
    find_parser.add_argument("--query", required=True)
    audit_parser = commands.add_parser("audit", help="Check structure, inventory and optional readiness markers")
    audit_parser.add_argument("project", type=Path)
    audit_parser.add_argument("--ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init(args.project, args.project_id)
        elif args.command == "find":
            result = find(args.project, args.query)
        else:
            result = audit(args.project, args.ready)
    except (Invalid, OSError, ValueError, TypeError, KeyError) as exc:
        result = {"ok": False, "errors": [str(exc)], "warnings": [WARNING]}
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
