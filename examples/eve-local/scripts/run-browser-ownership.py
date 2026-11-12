#!/usr/bin/env python3
"""Qualify two local browser gateways and one stopped Eve ownership restore."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen


sys.dont_write_bytecode = True
FIXTURE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("local_recovery", FIXTURE / "scripts/run-local-recovery.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
require = local.require


def db_state(path):
    require(path.is_file(), "Ownership database is missing")
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
    try:
        db.row_factory = sqlite3.Row
        integrity = [row[0] for row in db.execute("PRAGMA integrity_check")]
        require(integrity == ["ok"], "Ownership SQLite integrity check failed")
        return {"integrity": integrity,
                "store": dict(db.execute("SELECT * FROM ownership_store").fetchone()),
                "claims": [dict(row) for row in db.execute("SELECT * FROM ownership_claims ORDER BY claim_id")]}
    finally:
        db.close()


def session_inventory(app):
    root = app / ".eve/.workflow-data/streams/runs"
    return sorted(path.stem for path in root.glob("*.json"))


class Processes:
    def __init__(self, app, work, ports, environment, evidence, phase, fault_script=None):
        self.app, self.work, self.ports, self.environment = app, work, ports, environment
        self.evidence, self.phase, self.fault_script = evidence, phase, fault_script
        self.owned = []

    def start(self):
        require(all(local.port_free(port) for port in self.ports), "A fixture loopback port is occupied")
        for index, name in enumerate(("Eve", "G1", "G2")):
            port = self.ports[index]
            env = dict(self.environment)
            env["AGENT_FORGE_BROWSER_PORT"] = str(port)
            if index == 0:
                argv = [str(self.app / "node_modules/.bin/eve"), "dev", "--host", "127.0.0.1",
                        "--port", str(port), "--no-ui", "--no-default-extensions"]
                if self.phase == "restored":
                    argv.append("--resume")
            else:
                argv = ["node"]
                if index == 2 and self.fault_script:
                    argv.extend(("--import", str(self.fault_script)))
                argv.append("browser/serve.mjs")
            log = self.work / f"{self.phase}-{name}.log"
            with log.open("wb") as output:
                child = subprocess.Popen(argv, cwd=self.app, env=env, stdout=output,
                                         stderr=subprocess.STDOUT, start_new_session=True)
            self.owned.append((name, port, child))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                require(child.poll() is None, f"{name} exited {child.returncode}; see {log.name}")
                try:
                    if f"127.0.0.1:{port}" in log.read_text(encoding="utf-8", errors="replace"):
                        route = "/eve/v1/health" if index == 0 else "/"
                        with urlopen(f"http://127.0.0.1:{port}{route}", timeout=0.3) as response:
                            if index > 0 or json.load(response)["status"] == "ready":
                                break
                except (OSError, ValueError, KeyError):
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError(f"{name} did not start")
            require(os.getpgid(child.pid) == child.pid, "Owned process group mismatch")
            self.evidence.append({"event": "ready", "phase": self.phase, "role": name, "pid": child.pid,
                                  "port": port, "at": time.time(), "group": local.process_members(child.pid)})
        require(all(child.poll() is None and not local.port_free(port) for _, port, child in self.owned),
                "A fixture process stopped before all listeners were ready")

    def stop(self):
        failures = []
        for name, port, child in reversed(self.owned):
            try:
                if child.poll() is None:
                    require(os.getpgid(child.pid) == child.pid, "Owned process group mismatch")
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=7)
                    except subprocess.TimeoutExpired:
                        require(os.getpgid(child.pid) == child.pid, "Owned process group mismatch")
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=4)
                deadline = time.monotonic() + 3
                members = local.process_members(child.pid)
                while members and time.monotonic() < deadline:
                    time.sleep(0.05)
                    members = local.process_members(child.pid)
                free = local.port_free(port)
                require(not members and free, f"{name} group or listener remains active")
                self.evidence.append({"event": "stopped", "phase": self.phase, "role": name, "pid": child.pid,
                                      "port": port, "at": time.time(), "group": members, "port_free": free,
                                      "exit": child.returncode})
            except (RuntimeError, OSError, subprocess.SubprocessError) as error:
                failures.append(str(error))
        require(not failures, "; ".join(failures))


def observe(phase, app, work, ports, previous, values, expected, env):
    output = work / (phase + ".json")
    result = subprocess.run(["node", str(FIXTURE / "browser/check-ownership.mjs"), phase, str(app),
                             *map(str, ports), str(previous), str(output), json.dumps(values), str(expected)],
                            cwd=app, env=env, timeout=45)
    require(output.is_file(), f"Observer left no evidence for {phase}")
    data = local.read_json(output)
    require(result.returncode == 0 and data["status"] in {"passed", "stale-observed"},
            f"{phase} observer: {data.get('error', result.returncode)}")
    return data


def manage(app, command, path, env):
    return subprocess.run(["node", "browser/ownership.mjs", command, str(path)], cwd=app, env=env,
                          capture_output=True, text=True, timeout=10)


def seed(app, path, count, env):
    code = """
import { attachOwnership } from './browser/ownership.mjs';
const store = attachOwnership(process.argv[1]);
for (let index = 0; index < Number(process.argv[2]); index++) {
  if (!store.reserve("fixture-browser-a")) throw new Error("Unable to seed a private fixture reservation");
}
"""
    subprocess.run(["node", "--input-type=module", "-e", code, str(path), str(count)],
                   cwd=app, env=env, check=True, timeout=15)


def immutable_bindings(app, path, claims, env):
    code = """
import assert from "node:assert/strict";
import { attachOwnership } from './browser/ownership.mjs';
const store = attachOwnership(process.argv[1]);
for (const claim of JSON.parse(process.argv[2])) {
  store.finalize(claim.claim_id, claim.principal, claim.session_id);
  const other = claim.principal.endsWith("-a") ? "fixture-browser-b" : "fixture-browser-a";
  assert.throws(() => store.finalize(claim.claim_id, other, claim.session_id), /conflict/);
  assert.throws(() => store.finalize(claim.claim_id, claim.principal, "wrun_conflicting_identity"), /conflict/);
  assert.equal(store.owner(claim.session_id), claim.principal);
}
"""
    subprocess.run(["node", "--input-type=module", "-e", code, str(path), json.dumps(claims)],
                   cwd=app, env=env, check=True, timeout=15)


def restore_bundle(work, app, shared, dependencies, origins):
    bundle, quarantine = work / "bundle", work / "quarantine"
    bundle.mkdir()
    data = bundle / "data"
    data.mkdir()
    local.write_json(shared / "origins.json", origins)
    shutil.copytree(app, data / "app", symlinks=True,
                    ignore=lambda directory, _: {"node_modules"} if Path(directory) == app else set())
    shutil.copytree(shared, data / "shared", symlinks=True)
    entries = local.tree(data)
    manifest = bundle / "manifest.json"
    local.write_json(manifest, {"format": 1, "files": entries, "origins": origins})
    digest = local.sha(manifest)
    (bundle / "manifest.sha256").write_text(digest + "\n", encoding="ascii")
    require(local.sha(manifest) == digest and local.tree(data) == local.read_json(manifest)["files"],
            "Bundle content verification failed")
    for name in local.REQUIRED_STATE:
        require((data / "app" / name).is_dir(), f"Bundle missing {name}")
    require((data / "shared/owners.sqlite").is_file(), "Bundle missing ownership database")
    require(str(app) == origins["app"] and str(shared / "owners.sqlite") == origins["database"],
            "Same-path restore requires original absolute paths")
    for name, entry in entries.items():
        if name.startswith("app/") and "link" in entry:
            original = app / name.removeprefix("app/")
            target = Path(os.path.normpath(original.parent / entry["link"]))
            require(target.is_relative_to(app) or target.is_relative_to(dependencies), "Unsafe archived link")
    quarantine.mkdir()
    for name, path in (("app", app), ("shared", shared)):
        path.rename(quarantine / name)
        shutil.copytree(data / name, path, symlinks=True)
        archived = {key.removeprefix(name + "/"): value for key, value in entries.items()
                    if key.startswith(name + "/")}
        require(local.tree(path) == archived, f"Restored files differ: {name}")
    (app / "node_modules").symlink_to(dependencies, target_is_directory=True)
    return {"manifest_sha256": digest, "entries": len(entries), "quarantine": str(quarantine)}


def run(mode, source, dependencies, work, ports, values, expected, fault_script=None):
    names = local.source_paths(source)
    hashes = local.source_hashes(source, names)
    local.check_pins(source)
    versions = local.installed_pins(dependencies)
    require(not work.is_relative_to(source) and not work.is_relative_to(dependencies),
            "Choose an owned work directory outside source and dependencies")
    work.mkdir(mode=0o700)
    app, shared = work / "app", work / "shared"
    shared.mkdir()
    path = shared / "owners.sqlite"
    environment = {name: os.environ[name] for name in ("PATH", "HOME", "USER", "TMPDIR") if name in os.environ}
    environment.update(EVE_TELEMETRY_DISABLED="1", EVE_SCHEDULES_DISABLED="1",
                       AGENT_FORGE_BROWSER_TOKEN_A=secrets.token_urlsafe(32),
                       AGENT_FORGE_BROWSER_TOKEN_B=secrets.token_urlsafe(32),
                       AGENT_FORGE_FIXTURE_TOKEN=secrets.token_urlsafe(32),
                       AGENT_FORGE_FIXTURE_PORT=str(ports[0]), AGENT_FORGE_BROWSER_OWNERSHIP_DB=str(path),
                       AGENT_FORGE_TEST_FINALIZE_RECEIPT=str(work / "fault-receipt.json"))
    origins = {"app": str(app), "world": str(app / ".eve/.workflow-data"), "database": str(path),
               "ports": dict(zip(("Eve", "G1", "G2"), ports)), "versions": versions, "source_hashes": hashes}
    report = {"status": "running", "mode": mode, "origins": origins, "processes": []}
    try:
        local.copy_source(source, app, names, dependencies)
        subprocess.run(["node", "browser/build.mjs"], cwd=app, env=environment, check=True, timeout=15)
        legacy = app / ".eve/fixture-browser-owners.json"
        if mode != "baseline":
            legacy.parent.mkdir(exist_ok=True)
            legacy.write_text('[["wrun_legacy_fixture","fixture-browser-b"]]\n', encoding="utf-8")
            legacy_digest = local.sha(legacy)
            initialized = manage(app, "init", path, environment)
            require(initialized.returncode == 0, initialized.stderr)
            before_repeat = local.sha(path)
            repeated = manage(app, "init", path, environment)
            require(repeated.returncode == 2 and local.sha(path) == before_repeat, "Repeated init altered the store")
            report["initialization"] = {"first": json.loads(initialized.stdout), "repeat_exit": repeated.returncode}
        if mode == "capacity":
            seed(app, path, 255, environment)
            report["capacity_before"] = db_state(path)
        initial = Processes(app, work, ports, environment, report["processes"], "initial", fault_script)
        try:
            initial.start()
            if mode == "baseline":
                observe("baseline", app, work, ports, work / "unused", values, expected, environment)
            elif mode in {"capacity", "finalize"}:
                report["backend_before"] = session_inventory(app)
                observe(mode, app, work, ports, work / "fault-receipt.json", values, expected, environment)
                report["backend_after"] = session_inventory(app)
            else:
                prepared = observe("prepare", app, work, ports, work / "unused", values, expected, environment)
                if mode == "lifecycle":
                    retained = path.with_suffix(".retained")
                    path.rename(retained)
                    observe("unavailable", app, work, ports, work / "prepare.json", values, expected, environment)
                    (work / "unavailable.json").rename(work / "live-missing.json")
                    replacement = manage(app, "init", path, environment)
                    require(replacement.returncode == 0, replacement.stderr)
                    observe("unavailable", app, work, ports, work / "prepare.json", values, expected, environment)
                    (work / "unavailable.json").rename(work / "live-replaced.json")
                    report["retained_store"] = db_state(retained)
                else:
                    before = db_state(path)
                    expected_owners = {item["sessionId"]: "fixture-browser-" + name.lower()
                                       for name, item in prepared["sessions"].items()}
                    require({row["session_id"]: row["principal"] for row in before["claims"]} == expected_owners,
                            "Concurrent creates lost or changed a binding")
                    immutable_bindings(app, path, before["claims"], environment)
                    require(db_state(path) == before, "Immutable binding probe changed the store")
                    seed(app, path, 1, environment)
        finally:
            initial.stop()

        if mode == "qualify":
            report["before"] = db_state(path)
            report["original_sessions"] = session_inventory(app)
            require(set(report["original_sessions"]) == set(expected_owners), "Unexpected Eve session inventory")
            require(sum(row["session_id"] is None for row in report["before"]["claims"]) == 1,
                    "Missing pending claim before bundle")
            origins["receipts"] = {name: {"session": item["sessionId"], "owner": item["token"],
                                         "cursor": item["before"]["cursor"]}
                                   for name, item in prepared["sessions"].items()}
            shutil.copy2(work / "prepare.json", shared / "witness.json")
            report["bundle"] = restore_bundle(work, app, shared, dependencies, origins)
            require(db_state(path) == report["before"], "Ownership state changed before restored startup")
            restored = Processes(app, work, ports, environment, report["processes"], "restored")
            try:
                restored.start()
                require(not {child.pid for _, _, child in initial.owned} & {child.pid for _, _, child in restored.owned},
                        "Restored process identity was reused")
                observe("restore", app, work, ports, shared / "witness.json", values, expected, environment)
            finally:
                restored.stop()
            report["after"] = db_state(path)
            report["restored_sessions"] = session_inventory(app)
            require(report["after"] == report["before"] and report["restored_sessions"] == report["original_sessions"],
                    "Read-only restoration changed claims or backend session inventory")
        if mode == "capacity":
            report["after"] = db_state(path)
            require(len(report["after"]["claims"]) == 256
                    and sum(row["session_id"] is not None for row in report["after"]["claims"]) == 1,
                    "Capacity race admitted more than one owner or lost a pending claim")
            require(len(set(report["backend_after"]) - set(report["backend_before"])) == 1,
                    "Capacity race did not create exactly one backend session")
        if mode == "finalize":
            report["after"] = db_state(path)
            require(len(report["after"]["claims"]) == 1 and report["after"]["claims"][0]["session_id"] is None,
                    "Uncertain finalization did not preserve exactly one pending claim")
            witness = local.read_json(work / "fault-receipt.json")
            require(set(report["backend_after"]) - set(report["backend_before"]) == {witness["sessionId"]},
                    "Finalization fault created an unexpected number of backend sessions")
        if mode != "baseline":
            require(local.sha(legacy) == legacy_digest, "Legacy JSON changed")
            report["legacy_sha256_unchanged"] = legacy_digest
        require(local.source_hashes(source, names) == hashes and local.source_hashes(app, names) == hashes,
                "Fixture source changed")
        require(local.installed_pins(dependencies) == versions, "Installed pins changed")
        report["status"] = "stale-observed" if mode == "baseline" else "passed"
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError, sqlite3.Error) as error:
        report.update(status="failed", error=str(error))
        if path.is_file() and mode != "baseline":
            report["failure_store"] = db_state(path)
        report["failure_backend_sessions"] = session_inventory(app)
    finally:
        local.write_json(work / "result.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=FIXTURE)
    parser.add_argument("--dependencies", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--ports", type=int, nargs=3, required=True, metavar=("EVE", "G1", "G2"))
    parser.add_argument("--values", required=True)
    parser.add_argument("--expected", type=int, required=True)
    parser.add_argument("--baseline", action="store_true", help="Measure the old single-gateway fixture")
    args = parser.parse_args()
    try:
        values = json.loads(args.values)
        require(isinstance(values, list) and 1 <= len(values) <= 64
                and all(type(value) is int and abs(value) <= 1_000_000 for value in values),
                "Provide a bounded JSON integer array")
        require(sys.platform in {"darwin", "linux"} and len(set(args.ports)) == 3
                and all(1024 <= port <= 65535 for port in args.ports), "Use macOS or Linux and three distinct ports")
        source = args.source.resolve()
        dependencies = (args.dependencies or source / "node_modules").resolve()
        work = args.work_dir.resolve()
        report = run("baseline" if args.baseline else "qualify", source, dependencies,
                     work, args.ports, values, args.expected)
        result = {"status": report["status"], "evidence": str(work / "result.json")}
        if "error" in report:
            result["error"] = report["error"]
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        result = {"status": "failed", "error": str(error)}
    print(json.dumps(result))
    return int(result["status"] == "failed")


if __name__ == "__main__":
    sys.exit(main())
