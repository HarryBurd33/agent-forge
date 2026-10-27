"""Executed CLI contract checks, not model/task-quality tests."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "forge.py"


class ForgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.project = self.base / "report-agent"
        self.call("init", self.project, "--project-id", "report-agent")

    def call(self, *args, ok=True):
        run = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
        result = json.loads(run.stdout)
        self.assertEqual(run.returncode, 0 if ok else 1, run.stdout + run.stderr)
        self.assertEqual(result["ok"], ok)
        return result

    def read(self, name):
        return json.loads((self.project / name).read_text())

    def write(self, name, data):
        (self.project / name).write_text(json.dumps(data))

    def test_fresh_draft_audit_but_not_ready(self):
        result = self.call("audit", self.project)
        self.assertTrue(any("execution mode" in w for w in result["warnings"]))
        result = self.call("audit", self.project, "--ready", ok=False)
        self.assertTrue(any("placeholder" in e for e in result["errors"]))
        self.assertEqual(self.read("agent.json")["status"], "draft")

    def test_existing_destination_is_preserved(self):
        sentinel = self.project / "user-work.txt"
        sentinel.write_text("keep")
        self.call("init", self.project, "--project-id", "different", ok=False)
        self.assertEqual(sentinel.read_text(), "keep")
        empty = self.base / "empty"; empty.mkdir()
        self.call("init", empty, "--project-id", "empty", ok=False)

    def test_destination_traversal_and_symlink_refused(self):
        self.call("init", self.base / "report-agent" / ".." / "other", "--project-id", "other", ok=False)
        alias = self.base / "alias"; alias.symlink_to(self.project, target_is_directory=True)
        self.call("init", alias, "--project-id", "other", ok=False)
        self.call("init", alias / "new", "--project-id", "other", ok=False)

    def test_find_actual_contract_metadata(self):
        result = self.call("find", self.project, "--query", "operating source")
        self.assertEqual([r["id"] for r in result["matches"]], ["playbook"])
        self.assertEqual(self.call("find", self.project, "--query", "no-such-resource")["matches"], [])

    def test_missing_resource_unindexed_output_and_missing_evidence(self):
        (self.project / "AGENT.md").unlink()
        self.call("audit", self.project, ok=False)
        (self.project / "AGENT.md").write_text("restored")
        output = self.project / "report.md"; output.write_text("total 42")
        result = self.call("audit", self.project, ok=False)
        self.assertTrue(any("unindexed durable file: report.md" in e for e in result["errors"]))
        output.unlink()
        index = self.read("toolbox/index.json")
        index["resources"][0]["status"] = "validated"
        self.write("toolbox/index.json", index)
        self.call("audit", self.project, ok=False)
        index["resources"][0]["validation"]["evidence"] = ["missing.txt"]
        self.write("toolbox/index.json", index)
        self.call("audit", self.project, ok=False)

    def test_local_resource_escape_and_credential_paths(self):
        index = self.read("toolbox/index.json")
        for bad in ("../escape.txt", "/etc/passwd", ".env", "x\\bad.txt"):
            changed = copy.deepcopy(index); changed["resources"][0]["location"] = bad
            self.write("toolbox/index.json", changed)
            self.call("audit", self.project, ok=False)
        self.write("toolbox/index.json", index)
        outside = self.base / "outside.txt"; outside.write_text("outside")
        (self.project / "AGENT.md").unlink(); (self.project / "AGENT.md").symlink_to(outside)
        self.call("audit", self.project, ok=False)

    def test_explicit_zero_is_valid_missing_and_boolean_are_not(self):
        config = self.read("agent.json")
        config["bounds"].update(max_attempts=1, max_cost_usd=0, max_depth=0, max_concurrency=0, max_workers=0)
        self.write("agent.json", config)
        result = self.call("audit", self.project)
        self.assertTrue(any("Delegation disabled" in w for w in result["warnings"]))
        for key, value in (("max_attempts", 0), ("max_concurrency", False), ("max_minutes", None), ("max_cost_usd", -1)):
            changed = copy.deepcopy(config); changed["bounds"][key] = value
            self.write("agent.json", changed)
            self.call("audit", self.project, ok=False)
        del config["bounds"]["max_concurrency"]
        self.write("agent.json", config); self.call("audit", self.project, ok=False)

    def test_duplicate_ids_cycles_and_unknown_steps(self):
        index = self.read("toolbox/index.json")
        changed = copy.deepcopy(index); changed["resources"].append(copy.deepcopy(changed["resources"][0]))
        self.write("toolbox/index.json", changed); self.call("audit", self.project, ok=False)
        changed = copy.deepcopy(index); changed["resources"][1]["dependencies"] = ["instructions"]
        self.write("toolbox/index.json", changed); self.call("audit", self.project, ok=False)
        changed = copy.deepcopy(index); changed["resources"][0]["used_by"] = ["step-999"]
        self.write("toolbox/index.json", changed); self.call("audit", self.project, ok=False)

    def test_external_references_are_explicit_not_fetched(self):
        index = self.read("toolbox/index.json")
        entry = copy.deepcopy(index["resources"][1]); entry.update(id="external-template", kind="template", location="drive://file-123", dependencies=[])
        index["resources"].append(entry)
        self.write("toolbox/index.json", index); self.call("audit", self.project)
        # Synthetic URL parts exercise rejection without resembling a stored credential.
        userinfo_url = "https://" + "fixture-user" + ":" + "fixture-value" + "@example.com/file"
        for bad in ("http://example.com/file", userinfo_url, "https://example.com/file?token=value"):
            entry["location"] = bad; self.write("toolbox/index.json", index); self.call("audit", self.project, ok=False)

    def test_temporary_dirs_do_not_hide_durable_outputs(self):
        scratch = self.project / "scratch"; scratch.mkdir(); (scratch / "temp.txt").write_text("disposable")
        self.call("audit", self.project)
        config = self.read("agent.json"); config["retention"]["temporary_dirs"] = ["outputs"]
        self.write("agent.json", config); self.call("audit", self.project, ok=False)

    def test_claimed_registration_requires_receipt(self):
        config = self.read("agent.json"); config["execution"]["registration"]["status"] = "active"
        self.write("agent.json", config)
        result = self.call("audit", self.project, ok=False)
        self.assertTrue(any("claimed registration" in e for e in result["errors"]))

    def test_nested_durable_directory_cannot_escape_inventory(self):
        # Independent review exposed outputs/reports as an inventory bypass.
        config = self.read("agent.json")
        for directory in ("outputs/reports", "runs/run-02", "toolbox/templates"):
            nested = self.project / directory
            nested.mkdir(parents=True, exist_ok=True)
            (nested / "unindexed.md").write_text("durable result")
            config["retention"]["temporary_dirs"] = [directory]
            self.write("agent.json", config)
            result = self.call("audit", self.project, ok=False)
            self.assertTrue(any("cannot exclude durable" in e for e in result["errors"]))

    def test_ready_markers_pass_but_are_not_task_quality_evidence(self):
        config = self.read("agent.json")
        config.update(status="ready")
        config["execution"]["mode"] = "manual"
        config["authority"].update(source="Current test fixture", allowed=["local fixture only"])
        config["capabilities"]["observed"] = [name + ": fixture observation in evidence.md" for name in config["capabilities"]["required"]]
        self.write("agent.json", config)
        (self.project / "PLAYBOOK.md").write_text("# Report agent\nstep-01\n| check-01 | Sum equals 42 | Compare source rows | evidence.md |\n")
        evidence = self.project / "evidence.md"; evidence.write_text("Fixture structural evidence; no model run")
        index = self.read("toolbox/index.json")
        for entry in index["resources"]:
            entry["status"] = "validated"
            entry["validation"]["evidence"] = ["evidence.md"]
        entry = copy.deepcopy(index["resources"][1])
        entry.update(id="evidence", kind="evidence", location="evidence.md", dependencies=[], status="draft")
        entry["validation"]["evidence"] = []
        index["resources"].append(entry)
        self.write("toolbox/index.json", index)
        result = self.call("audit", self.project, "--ready")
        self.assertTrue(any("does not establish task quality" in w for w in result["warnings"]))
        config["capabilities"].update(optional=["scheduler"], missing=["scheduler"])
        self.write("agent.json", config)
        optional_result = self.call("audit", self.project, "--ready")
        self.assertTrue(any("Optional capabilities unavailable: scheduler" in w for w in optional_result["warnings"]))
        config["capabilities"]["missing"].append("artifact-read-write")
        self.write("agent.json", config)
        self.call("audit", self.project, "--ready", ok=False)
        config["capabilities"]["missing"] = ["scheduler"]
        config["capabilities"]["observed"] = ["unrelated-tool"]
        self.write("agent.json", config)
        self.call("audit", self.project, "--ready", ok=False)

    def test_malformed_json_and_types_fail_as_json(self):
        for invalid in ("[]", "{", '{"schema_version":NaN}'):
            (self.project / "agent.json").write_text(invalid)
            self.call("audit", self.project, ok=False)


if __name__ == "__main__":
    unittest.main()
