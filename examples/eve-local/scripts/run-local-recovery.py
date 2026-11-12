#!/usr/bin/env python3
"""Qualify local two-world Eve admission and quiescent same-path recovery."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import sqlite3
import stat
import subprocess
import sys
import time
from urllib.request import urlopen


PINS = {"eve": "1.0.0-rc.9", "just-bash": "3.6.0", "rolldown": "1.2.16"}
REQUIRED_STATE = (".eve/.workflow-data", ".eve/dev-runtime/snapshots", ".eve/dev-hosts")
FIXTURE = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def regular_file(path):
    return not path.is_symlink() and path.is_file() and path.resolve() == path


def source_paths(root):
    index = root / "toolbox/index.json"
    require(regular_file(index), "Missing regular fixture toolbox index")
    names = [row["location"] for row in read_json(index)["resources"]]
    require(len(names) == len(set(names)) and "toolbox/index.json" in names, "Invalid fixture toolbox")
    for name in names:
        path = root / name
        require(Path(name).as_posix() == name and not Path(name).is_absolute() and ".." not in Path(name).parts
                and Path(name).parts and Path(name).parts[0] not in {"node_modules", ".eve", ".git", ".output"}
                and regular_file(path), f"Unsafe or missing indexed source: {name}")
    return sorted(names)


def source_hashes(root, names):
    return {name: sha(root / name) for name in names}


def check_pins(app):
    manifest_path, lock_path = app / "package.json", app / "package-lock.json"
    require(regular_file(manifest_path) and regular_file(lock_path), "Missing regular fixture package pins")
    manifest = read_json(manifest_path)
    lock = read_json(lock_path)["packages"]
    declared = {**manifest["dependencies"], **manifest["devDependencies"]}
    for package, version in PINS.items():
        require(declared.get(package) == version and lock[f"node_modules/{package}"]["version"] == version,
                f"Manifest/lock pin mismatch: {package}")


def installed_pins(dependencies):
    for package, version in PINS.items():
        require(read_json(dependencies / package / "package.json")["version"] == version,
                f"Installed dependency pin mismatch: {package}")
    node = subprocess.check_output(["node", "-p", "process.versions.node"], text=True, timeout=5).strip()
    require(node.startswith("24."), "Node 24 is required")
    return {"node": node, **PINS}


def copy_source(source, target, names, dependencies):
    target.mkdir()
    for name in names:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, path)
    (target / "node_modules").symlink_to(dependencies, target_is_directory=True)


def tree(root):
    entries = {}

    def visit(directory):
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                entries[relative] = {"link": os.readlink(path)}
            elif stat.S_ISDIR(info.st_mode):
                entries[relative] = {"mode": stat.S_IMODE(info.st_mode), "directory": True}
                visit(path)
            elif stat.S_ISREG(info.st_mode):
                entries[relative] = {"mode": stat.S_IMODE(info.st_mode), "sha256": sha(path)}
            else:
                raise RuntimeError(f"Unsupported bundle entry: {relative}")
    visit(root)
    return entries


def inventory_diff(expected, actual):
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    changed = sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name])
    return {"missing": missing[:12], "extra": extra[:12], "changed": changed[:12]}


def verify_bundle(bundle):
    manifest = bundle / "manifest.json"
    checksum = bundle / "manifest.sha256"
    require(regular_file(manifest) and regular_file(checksum), "Bundle manifest or checksum is missing")
    require(sha(manifest) == checksum.read_text(encoding="ascii").strip(),
            "Bundle manifest checksum mismatch")
    expected = read_json(manifest)
    require(expected["format"] == 1, "Unsupported bundle format")
    data = bundle / "data"
    require(data.is_dir() and not data.is_symlink(), "Bundle data directory is missing")
    actual = tree(data)
    require(actual == expected["files"], f"Bundle mismatch: {inventory_diff(expected['files'], actual)}")
    for name in ("ledger.sqlite", "origins.json", "witness.json"):
        require(regular_file(data / "shared" / name), f"Missing bundle state: {name}")
    origins = read_json(data / "shared" / "origins.json")
    require(origins["versions"] == expected["versions"] and all(
        expected["versions"].get(name) == version for name, version in PINS.items()
    ), "Bundle version mismatch")
    require(isinstance(expected["versions"].get("node"), str) and expected["versions"]["node"].startswith("24."),
            "Bundle Node version mismatch")
    apps = origins["apps"]
    require(set(apps) == {"A", "B"} and apps["A"] != apps["B"], "Bundle needs two distinct origins")
    require(set(origins["worlds"]) == {"A", "B"} and set(origins["ports"]) == {"A", "B"},
            "Bundle origin map is incomplete")
    dependencies = Path(origins["dependency_root"])
    require(dependencies.is_absolute(), "Bundle dependency root must be absolute")
    for origin in ("A", "B"):
        archived = data / origin
        app = Path(apps[origin])
        require(app.is_absolute() and str(app / ".eve/.workflow-data") == origins["worlds"][origin],
                f"Bundle world path mismatch: {origin}")
        require(all((archived / name).is_dir() and (archived / name).resolve() == archived / name
                    for name in REQUIRED_STATE), f"Bundle workflow state is incomplete: {origin}")
        require(not (archived / "node_modules").exists(), "Bundle must not embed dependencies")
        check_pins(archived)
        require(source_hashes(archived, source_paths(archived)) == expected["sources"],
                f"Bundle source mismatch: {origin}")
        for name, entry in actual.items():
            relative = Path(name)
            if relative.parts[0] == origin and "link" in entry:
                original = app.joinpath(*relative.parts[1:])
                target = Path(os.path.normpath(original.parent / entry["link"]))
                require(target.is_relative_to(app) or target.is_relative_to(dependencies),
                        f"Bundle link would reach outside the app and pinned dependencies: {name}")
    witness = read_json(data / "shared" / "witness.json")
    require(witness["status"] == "passed" and witness["phase"] == "prepare", "Missing original receipt witness")
    require(set(origins["launches"]) == set(witness["original"]), "Bundle launch map is incomplete")
    return expected, origins


def make_bundle(bundle, apps, shared, versions, hashes):
    bundle.mkdir()
    data = bundle / "data"
    data.mkdir()
    for origin, app in apps.items():
        shutil.copytree(app, data / origin, symlinks=True,
                        ignore=lambda directory, _: {"node_modules"} if Path(directory) == app else set())
    shutil.copytree(shared, data / "shared", symlinks=True)
    manifest = bundle / "manifest.json"
    write_json(manifest, {"format": 1, "versions": versions, "sources": hashes, "files": tree(data)})
    (bundle / "manifest.sha256").write_text(sha(manifest) + "\n", encoding="ascii")
    return verify_bundle(bundle)


def restore_bundle(bundle, apps, shared, dependencies, quarantine, versions):
    expected, origins = verify_bundle(bundle)
    require(expected["versions"] == versions, "Restore runtime versions changed")
    require(origins["apps"] == {key: str(value) for key, value in apps.items()}
            and origins["ledger"] == str(shared / "ledger.sqlite")
            and origins["dependency_root"] == str(dependencies), "Restore paths differ from captured paths")
    quarantine.mkdir()
    destinations = {**apps, "shared": shared}
    for name, path in destinations.items():
        path.rename(quarantine / name)
    for name, path in destinations.items():
        shutil.copytree(bundle / "data" / name, path, symlinks=True)
        archived = {k.removeprefix(name + "/"): value for k, value in expected["files"].items()
                    if k.startswith(name + "/")}
        require(tree(path) == archived, f"Restored bytes differ: {name}")
    for app in apps.values():
        (app / "node_modules").symlink_to(dependencies, target_is_directory=True)
    return expected


def ledger_state(path):
    require(path.is_file(), "Original SQLite ledger is missing")
    database = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
    try:
        database.row_factory = sqlite3.Row
        integrity = [row[0] for row in database.execute("PRAGMA integrity_check")]
        require(integrity == ["ok"], "SQLite integrity check failed")
        return {"integrity": integrity,
                "budgets": [dict(row) for row in database.execute("SELECT * FROM budgets ORDER BY budget_id")],
                "launches": [dict(row) for row in database.execute("SELECT * FROM launches ORDER BY budget_id, launch_id")]}
    finally:
        database.close()


def process_members(pid):
    rows = subprocess.check_output(["ps", "-axo", "pid=,ppid=,pgid=,stat="], text=True, timeout=4)
    members = []
    for line in rows.splitlines():
        process, parent, group, state = line.split()
        if int(group) == pid and not state.startswith("Z"):
            members.append({"pid": int(process), "ppid": int(parent), "pgid": int(group)})
    return members


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as error:
            if error.errno == errno.EADDRINUSE:
                return False
            raise OSError(error.errno, f"Could not inspect 127.0.0.1:{port}: {error.strerror}") from error
        return True


class Servers:
    def __init__(self, work, apps, ports, environment, evidence, resume=False):
        self.work, self.apps, self.ports = work, apps, ports
        self.environment, self.evidence, self.resume = environment, evidence, resume
        self.owned = []

    def start(self):
        require(all(port_free(port) for port in self.ports.values()), "A requested port is unavailable")
        for origin, app in self.apps.items():
            port = self.ports[origin]
            log = self.work / f"{'restore' if self.resume else 'initial'}-{origin}.log"
            argv = [str(app / "node_modules/.bin/eve"), "dev", "--host", "127.0.0.1", "--port", str(port),
                    "--no-ui", "--no-default-extensions"]
            if self.resume:
                argv.append("--resume")
            with log.open("wb") as output:
                process = subprocess.Popen(argv, cwd=app, env=self.environment, stdout=output,
                                           stderr=subprocess.STDOUT, start_new_session=True)
            self.owned.append((origin, process, log))
        deadline = time.monotonic() + 35
        for origin, process, log in self.owned:
            port = self.ports[origin]
            while time.monotonic() < deadline:
                require(process.poll() is None, f"Origin {origin} exited {process.returncode}; see {log.name}")
                try:
                    if f"127.0.0.1:{port}" in log.read_text(encoding="utf-8", errors="replace"):
                        with urlopen(f"http://127.0.0.1:{port}/eve/v1/health", timeout=0.4) as response:
                            if json.load(response)["status"] == "ready":
                                break
                except (OSError, ValueError, KeyError):
                    pass
                time.sleep(0.15)
            else:
                raise RuntimeError(f"Origin {origin} did not become ready")
            require(os.getpgid(process.pid) == process.pid, "Owned process group mismatch")
            self.evidence.append({"event": "ready", "at": time.time(), "origin": origin, "pid": process.pid,
                                  "port": port, "group": process_members(process.pid), "resume": self.resume})
        require(len({process.pid for _, process, _ in self.owned}) == 2, "Expected two distinct PIDs")
        for origin, process, _ in self.owned:
            require(process.poll() is None and not port_free(self.ports[origin]),
                    f"Origin {origin} stopped before both listeners were ready")

    def stop(self):
        failures = []
        for origin, process, _ in self.owned:
            try:
                if process.poll() is None:
                    require(os.getpgid(process.pid) == process.pid, "Owned process group mismatch")
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=7)
                    except subprocess.TimeoutExpired:
                        require(os.getpgid(process.pid) == process.pid, "Owned process group mismatch")
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=4)
                end = time.monotonic() + 3
                members = process_members(process.pid)
                while members and time.monotonic() < end:
                    time.sleep(0.05)
                    members = process_members(process.pid)
                free = port_free(self.ports[origin])
                require(not members and free, f"Origin {origin} group or listener remains active")
                self.evidence.append({"event": "stopped", "at": time.time(), "origin": origin, "pid": process.pid,
                                      "exit": process.returncode, "port_free": free, "group": members})
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                failures.append(str(error))
        require(not failures, "; ".join(failures))


def run_observer(phase, app, ports, witness, report, values, expected, environment):
    result = subprocess.run(
        ["node", str(FIXTURE / "scripts/check-local-recovery.mjs"), phase, str(app),
         str(ports["A"]), str(ports["B"]), str(witness), str(report), json.dumps(values), str(expected)],
        env=environment, timeout=55, check=False,
    )
    require(report.is_file(), f"{phase} observer produced no evidence")
    observation = read_json(report)
    require(result.returncode == 0 and observation["status"] == "passed",
            f"{phase} observer failed: {observation.get('error', result.returncode)}")
    return observation


def verify_originals(original, ledger, expected):
    by_key = {(row["budget_id"], row["launch_id"]): row for row in ledger["launches"]}
    require(len(by_key) == len(original) == 4, "Unexpected admission count")
    for label, item in original.items():
        run = item["run"]
        row = by_key[(run["budgetId"], run["launchId"])]
        require(row["parent_session_id"] == run["sessionId"]
                and json.loads(row["identity"]) == {name: run[name] for name in ("budgetId", "launchId", "mode", "values")},
                f"Original ledger identity changed: {label}")
        state = "completed" if label in {"completed", "origin-demo"} else "uncertain"
        require(row["state"] == state, f"Unexpected ledger state: {label}")
        handles = item.get("witness", {}).get("handles", {})
        require(row["child_session_id"] == handles.get("childSessionId"), f"Original child changed: {label}")
        if state == "completed":
            require(json.loads(row["result"]) == {"launchId": run["launchId"], "total": expected, "tools": ["scoped_total"]},
                    f"Original result differs: {label}")
        else:
            require(row["result"] is None, f"Pending result was fabricated: {label}")


def verify_restore(before, after, original, expected):
    require(after["budgets"] == before["budgets"], "Restore changed the admission budgets")
    target = original["restore-uncertain"]["witness"]["handles"]
    expected_launches = [dict(row) for row in before["launches"]]
    row = next(row for row in expected_launches if row["budget_id"] == "restore-uncertain")
    row.update(state="completed", child_delivery_id=target["childDeliveryId"])
    result = {"launchId": row["launch_id"], "total": expected, "tools": ["scoped_total"]}
    row["result"] = json.dumps(result, separators=(",", ":"))
    require(after["launches"] == expected_launches, "Restore changed another launch, duplicated an effect, or lost a handle")


def qualify(source, dependencies, work, ports, values, expected):
    names = source_paths(source)
    hashes = source_hashes(source, names)
    check_pins(source)
    versions = installed_pins(dependencies)
    require(not work.is_relative_to(source) and not work.is_relative_to(dependencies),
            "Choose a private work directory outside the source and dependency roots")
    work.mkdir(mode=0o700)
    report = {"status": "running", "versions": versions, "processes": [], "source_hashes": hashes,
              "ports": ports, "values": values, "expected": expected}
    apps = {name: work / name for name in ("A", "B")}
    shared = work / "shared"
    shared.mkdir()
    ledger = shared / "ledger.sqlite"
    witness = shared / "witness.json"
    environment = {name: os.environ[name] for name in ("PATH", "HOME", "USER", "TMPDIR") if name in os.environ}
    environment.update(EVE_TELEMETRY_DISABLED="1", EVE_SCHEDULES_DISABLED="1",
                       AGENT_FORGE_FIXTURE_TOKEN=secrets.token_urlsafe(32), AGENT_FORGE_DELEGATION_DB=str(ledger))
    try:
        for app in apps.values():
            copy_source(source, app, names, dependencies)
        origins = {"apps": {key: str(value) for key, value in apps.items()},
                   "worlds": {key: str(value / ".eve/.workflow-data") for key, value in apps.items()},
                   "ports": ports, "ledger": str(ledger), "versions": versions, "dependency_root": str(dependencies)}
        report["topology"] = origins.copy()
        initial = Servers(work, apps, ports, environment, report["processes"])
        try:
            initial.start()
            before = run_observer("prepare", apps["A"], ports, witness, witness, values, expected, environment)
        finally:
            initial.stop()
        report["before"] = ledger_state(ledger)
        verify_originals(before["original"], report["before"], expected)
        origins["launches"] = {name: {"origin": item["run"]["origin"], "budgetId": item["run"]["budgetId"],
                                     "launchId": item["run"]["launchId"], "parentSessionId": item["run"]["sessionId"],
                                     **item.get("witness", {}).get("handles", {})}
                               for name, item in before["original"].items()}
        write_json(shared / "origins.json", origins)
        bundle = work / "bundle"
        make_bundle(bundle, apps, shared, versions, hashes)
        report["bundle_sha256"] = sha(bundle / "manifest.json")
        report["bundle_files"] = len(restore_bundle(bundle, apps, shared, dependencies, work / "quarantine", versions)["files"])
        report["restored_before_start"] = ledger_state(ledger)
        require(report["restored_before_start"] == report["before"], "Restored SQLite state differs before startup")
        resumed = Servers(work, apps, ports, environment, report["processes"], resume=True)
        try:
            resumed.start()
            require(not {item[1].pid for item in initial.owned} & {item[1].pid for item in resumed.owned},
                    "Restore did not obtain new process identities")
            run_observer("restore", apps["A"], ports, witness, work / "restored-witness.json", values, expected, environment)
        finally:
            resumed.stop()
        report["after"] = ledger_state(ledger)
        verify_restore(report["before"], report["after"], before["original"], expected)
        require(source_hashes(source, names) == hashes and all(source_hashes(app, names) == hashes for app in apps.values()),
                "Fixture source changed during qualification")
        require(installed_pins(dependencies) == versions, "Dependency versions changed")
        report["status"] = "passed"
    except (KeyError, OSError, RuntimeError, ValueError, subprocess.SubprocessError, sqlite3.Error) as error:
        report.update(status="failed", error=str(error))
        if ledger.is_file():
            try:
                report["failure_ledger"] = ledger_state(ledger)
            except (OSError, RuntimeError, sqlite3.Error) as ledger_error:
                report["failure_ledger_error"] = str(ledger_error)
    finally:
        write_json(work / "result.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-bundle", type=Path, help="Verify an existing bundle without launching a runtime")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--dependencies", type=Path, help="Existing pinned node_modules directory")
    parser.add_argument("--work-dir", type=Path, help="New private work directory with an existing parent")
    parser.add_argument("--ports", nargs=2, type=int, metavar=("A", "B"))
    parser.add_argument("--values", help="JSON integer array")
    parser.add_argument("--expected", type=int, help="Independently computed expected total")
    args = parser.parse_args(argv)
    try:
        if args.verify_bundle:
            require(not any((args.source, args.work_dir, args.ports, args.values, args.dependencies)) and args.expected is None,
                    "Bundle verification does not accept execution arguments")
            manifest, _ = verify_bundle(args.verify_bundle.resolve())
            result = {"status": "verified", "files": len(manifest["files"]), "versions": manifest["versions"]}
        else:
            require(args.work_dir and args.ports and args.values and args.expected is not None,
                    "Run mode requires --work-dir, --ports, --values and --expected")
            require(sys.platform in {"darwin", "linux"}, "Local process qualification requires macOS or Linux")
            require(len(set(args.ports)) == 2 and all(1024 <= port <= 65535 for port in args.ports),
                    "Choose two distinct unprivileged loopback ports")
            values = json.loads(args.values)
            require(isinstance(values, list) and 1 <= len(values) <= 64
                    and all(type(value) is int and abs(value) <= 1_000_000 for value in values),
                    "Use 1–64 fixture integers within ±1,000,000")
            source = (args.source or FIXTURE).resolve()
            dependencies = (args.dependencies or source / "node_modules").resolve()
            work = args.work_dir.resolve()
            result = qualify(source, dependencies, work, dict(zip(("A", "B"), args.ports)), values, args.expected)
            result = {key: value for key, value in result.items() if key in {"status", "error", "versions", "bundle_sha256"}}
            result["evidence"] = str(work / "result.json")
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, subprocess.SubprocessError) as error:
        result = {"status": "failed", "error": str(error)}
    if result["status"] == "failed" and args.verify_bundle:
        print(json.dumps(result), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return int(result["status"] == "failed")


if __name__ == "__main__":
    sys.exit(main())
