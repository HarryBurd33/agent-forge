import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PROVIDER = os.environ["AGENT_FORGE_TEST_PROVIDER"]
CASES = {"lost_ack", "conflict", "unknown", "not_committed"}
PAYLOAD = json.dumps({"total": 13}, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
IDENTITY = {"key": "op-17", "action": "deliver", "target": "local-outbox-blue",
            "payload_sha256": hashlib.sha256(PAYLOAD.encode("utf-8")).hexdigest(),
            "source_version": "rows-v2"}

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(path, data):
    temp = path.with_suffix(".tmp")
    with temp.open("w") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def main(case, mode):
    if case not in CASES or mode not in {"start", "recover"}:
        raise ValueError("invalid case or mode")
    path = ROOT / (case + ".json")
    if path.exists():
        state = json.loads(path.read_text())
        if mode != "recover" or state["outcome"] not in {"uncertain", "still_unknown"} or state["intent"] != IDENTITY or state["case"] != case or state["payload_json"] != PAYLOAD:
            raise ValueError("existing state does not authorize this transition")
    else:
        if (mode == "start") != (case == "lost_ack"):
            raise ValueError("lost_ack must start once before recovering")
        state = {"case": case, "intent": IDENTITY, "payload_json": PAYLOAD,
                 "intent_saved_at": now(), "intent_writer_pid": os.getpid(),
                 "calls": [], "outcome": "prepared" if mode == "start" else "uncertain"}
        save(path, state)

    def call(operation):
        if len(state["calls"]) >= 3:
            raise ValueError("provider call limit reached")
        args = [sys.executable, PROVIDER, "--case", case, operation, "--key", IDENTITY["key"]]
        if operation == "send":
            args.extend(["--action", IDENTITY["action"], "--target", IDENTITY["target"],
                         "--payload-json", PAYLOAD, "--source-version", IDENTITY["source_version"]])
        observed = json.loads(path.read_text())
        assert observed["intent"] == IDENTITY and observed["payload_json"] == PAYLOAD
        event = {"command": args, "runner_pid": os.getpid(), "reserved_at": now(),
                 "intent_on_disk_before_call_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        state["calls"].append(event)
        state["outcome"] = "uncertain"
        save(path, state)
        with subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as child:
            event["provider_pid"] = child.pid
            stdout, stderr = child.communicate(timeout=12)
            event.update(exit_code=child.returncode, stdout=stdout, stderr=stderr, ended_at=now())
        save(path, state)
        try:
            observation = json.loads(stdout)
        except ValueError:
            observation = {}
        return event["exit_code"], observation if isinstance(observation, dict) else {}

    def finish(outcome, detail, code=0):
        state.update(outcome=outcome, detail=detail, terminal_runner_pid=os.getpid(), updated_at=now())
        save(path, state)
        print(json.dumps({"case": case, "outcome": outcome, "detail": detail, "calls": len(state["calls"]), "runner_pid": os.getpid()}))
        return code

    def mismatch(observed):
        return [key for key, value in IDENTITY.items() if observed.get(key) != value]

    def send():
        code, observed = call("send")
        if code == 75:
            return finish("uncertain", "Acknowledgement lost. Recovery must begin with lookup.", 75)
        if code == 73:
            return finish("identity_conflict", "Provider rejected send due to existing identity conflict.")
        if code == 0 and observed.get("status") == "committed":
            if mismatch(observed):
                return finish("identity_conflict", {"mismatched_fields": mismatch(observed)})
            if isinstance(observed.get("receipt"), str) and observed["receipt"]:
                return finish("verified_delivered", {"receipt": observed["receipt"], "evidence": "matching provider acknowledgement"})
        return finish("uncertain", "Send did not yield an authoritative matching receipt.", 1)

    if mode == "start":
        return send()
    code, observed = call("lookup")
    status = observed.get("status")
    if code != 0:
        return finish("uncertain", "Lookup unavailable or failed.", 1)
    if status == "unknown" and observed.get("key") == IDENTITY["key"]:
        return finish("still_unknown", "Provider did not establish commit or noncommit.")
    if status in {"committed", "terminal_not_committed"}:
        if mismatch(observed):
            return finish("identity_conflict", {"mismatched_fields": mismatch(observed)})
        if status == "terminal_not_committed":
            return send()
        if isinstance(observed.get("receipt"), str) and observed["receipt"]:
            return finish("reconciled_prior_commit", {"receipt": observed["receipt"], "evidence": "matching provider lookup"})
    return finish("uncertain", "Lookup did not yield authoritative evidence for the saved intent.", 1)

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
