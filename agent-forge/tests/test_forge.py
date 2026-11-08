"""Executed CLI contract checks, not model/task-quality tests."""
import copy
import hashlib
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

    def test_legacy_index_without_freshness_bindings_remains_compatible(self):
        index = self.read("toolbox/index.json")
        for entry in index["resources"]:
            entry["validation"].pop("bindings", None)
        self.write("toolbox/index.json", index)
        self.call("audit", self.project)

    def test_freshness_bindings_accept_unchanged_and_reject_stale_source_and_evidence(self):
        index = self.read("toolbox/index.json")
        entry = index["resources"][0]
        source = self.project / "AGENT.md"
        evidence = self.project / "PLAYBOOK.md"
        original_source = source.read_text()
        original_evidence = evidence.read_text()
        entry["validation"]["evidence"] = ["PLAYBOOK.md"]
        entry["validation"]["bindings"] = [
            {"role": "source", "location": "AGENT.md", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
            {"role": "evidence", "location": "PLAYBOOK.md", "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()},
        ]
        self.write("toolbox/index.json", index)
        self.call("audit", self.project)

        source.write_text(original_source + "\nchanged source\n")
        result = self.call("audit", self.project, ok=False)
        self.assertTrue(any("stale source binding AGENT.md" in error for error in result["errors"]))
        source.write_text(original_source)

        evidence.write_text(original_evidence + "\nchanged evidence\n")
        result = self.call("audit", self.project, ok=False)
        self.assertTrue(any("stale evidence binding PLAYBOOK.md" in error for error in result["errors"]))

    def test_freshness_bindings_reject_bad_digests_and_unlisted_evidence(self):
        index = self.read("toolbox/index.json")
        entry = index["resources"][0]
        evidence_sha = hashlib.sha256((self.project / "AGENT.md").read_bytes()).hexdigest()
        entry["validation"]["evidence"] = ["PLAYBOOK.md"]
        entry["validation"]["bindings"] = [
            {"role": "evidence", "location": "AGENT.md", "sha256": evidence_sha}
        ]
        self.write("toolbox/index.json", index)
        result = self.call("audit", self.project, ok=False)
        self.assertTrue(any("evidence binding must appear in validation.evidence" in error for error in result["errors"]))

        entry["validation"]["bindings"][0]["sha256"] = "not-a-hash"
        self.write("toolbox/index.json", index)
        result = self.call("audit", self.project, ok=False)
        self.assertTrue(any("binding sha256 must be 64 hexadecimal characters" in error for error in result["errors"]))

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


class RunRecordTests(unittest.TestCase):
    """Black-box conformance probes; these do not establish task outcome truth."""
    call = ForgeTests.call

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / "evidence.txt").write_text("synthetic independent result")
        # Criteria live outside the project and are explicitly selected by the reviewer.
        self.criteria_path = self.base / "reviewer-criteria.json"
        self.criteria = {"checks": [{"id": "check-01", "expected": 0, "method": "Compare source sum"}]}
        self.record = {"status": "passed", "checks": [{"id": "check-01", "expected": 0,
                       "method": "Compare source sum", "status": "pass", "evidence": ["evidence.txt"],
                       "observed": 0}]}

    def audit_record(self, record=None, criteria=None, ok=True, digest=None, record_path="review.json"):
        self.criteria_path.write_text(json.dumps(self.criteria if criteria is None else criteria))
        if record_path == "review.json":
            (self.project / record_path).write_text(json.dumps(self.record if record is None else record))
        pinned = hashlib.sha256(self.criteria_path.read_bytes()).hexdigest() if digest is None else digest
        return self.call("audit-run", self.project, "--record", record_path, "--criteria",
                         self.criteria_path, "--criteria-sha256", pinned, ok=ok)

    def test_complete_zero_false_and_optional_checks(self):
        self.audit_record()
        numeric_record = copy.deepcopy(self.record)
        numeric_record["checks"][0]["expected"] = 0.0
        self.audit_record(numeric_record)  # JSON has one numeric type, distinct from Boolean.
        false_record = copy.deepcopy(self.record)
        false_record["checks"][0].update(expected=False, observed=False)
        false_criteria = copy.deepcopy(self.criteria)
        false_criteria["checks"][0]["expected"] = False
        result = self.audit_record(false_record, false_criteria)
        self.assertTrue(any("conformance only" in warning for warning in result["warnings"]))
        false_criteria["checks"].append({"id": "optional", "expected": None, "method": "Optional inspection", "required": False})
        self.audit_record(false_record, false_criteria)
        remote = copy.deepcopy(self.record)
        remote["checks"][0]["evidence"] = ["https://example.com/public-result"]
        self.audit_record(remote)

    def test_a1_omitted_fields_and_pass_evidence(self):
        for field in ("method", "evidence", "observed", "expected", "status", "id"):
            with self.subTest(missing=field):
                changed = copy.deepcopy(self.record)
                del changed["checks"][0][field]
                self.audit_record(changed, ok=False)
        for evidence, observed in (([], 0), (["evidence.txt"], None)):
            changed = copy.deepcopy(self.record)
            changed["checks"][0].update(evidence=evidence, observed=observed)
            self.audit_record(changed, ok=False)

    def test_failed_partial_records_and_required_success(self):
        for run_status in ("partial", "failed", "blocked", "uncertain", "planned", "running"):
            for check_status in ("fail", "blocked", "unavailable", "not_run"):
                with self.subTest(run=run_status, check=check_status):
                    changed = copy.deepcopy(self.record)
                    changed["status"] = run_status
                    changed["checks"][0].update(status=check_status, evidence=[], observed=None)
                    result = self.audit_record(changed)
                    self.assertTrue(any("incomplete or failed" in w for w in result["warnings"]))
        changed["status"] = "passed"
        self.audit_record(changed, ok=False)
        changed["checks"] = []
        changed["status"] = "blocked"
        self.audit_record(changed, ok=False)

    def test_frozen_values_types_methods_and_pinned_bytes(self):
        for expected in (False, "0", None, [0], {"value": 0}):
            changed = copy.deepcopy(self.record)
            changed["checks"][0]["expected"] = expected
            self.audit_record(changed, ok=False)
        # Nested Boolean/number differences must also be rejected.
        criteria = copy.deepcopy(self.criteria)
        criteria["checks"][0]["expected"] = {"rows": [False]}
        changed = copy.deepcopy(self.record)
        changed["checks"][0]["expected"] = {"rows": [0]}
        self.audit_record(changed, criteria, ok=False)
        for method in ("Changed oracle", False, " ", []):
            changed = copy.deepcopy(self.record)
            changed["checks"][0]["method"] = method
            self.audit_record(changed, ok=False)
        for digest in ("0" * 64, "not-a-digest"):
            result = self.audit_record(ok=False, digest=digest, record_path="missing-record.json")
            self.assertTrue(any("criteria" in e for e in result["errors"]))
            self.assertFalse(any("missing-record" in e for e in result["errors"]))

    def test_duplicate_unknown_and_invalid_statuses(self):
        changed = copy.deepcopy(self.record)
        changed["checks"].append(copy.deepcopy(changed["checks"][0]))
        self.audit_record(changed, ok=False)
        criteria = copy.deepcopy(self.criteria)
        criteria["checks"].append(copy.deepcopy(criteria["checks"][0]))
        self.audit_record(criteria=criteria, ok=False)
        for field, value in (("id", "unknown-check"), ("status", "unsupported-status"), ("status", True)):
            changed = copy.deepcopy(self.record)
            changed["checks"][0][field] = value
            self.audit_record(changed, ok=False)
        changed = copy.deepcopy(self.record)
        changed["status"] = "success"
        self.audit_record(changed, ok=False)

    def test_optional_not_applicable_requires_explanation_and_frozen_optionality(self):
        criteria = copy.deepcopy(self.criteria)
        criteria["checks"].append({"id": "optional", "expected": "Only for published inputs",
                                   "method": "Inspect publication state", "required": False})
        record = copy.deepcopy(self.record)
        record["checks"].append({"id": "optional", "expected": "Only for published inputs",
                                  "method": "Inspect publication state", "status": "not_applicable",
                                  "evidence": [], "observed": "Input is an unpublished local fixture."})
        self.audit_record(record, criteria)
        for explanation in (None, "", "  ", False, 0, [], {}):
            with self.subTest(explanation=explanation):
                changed = copy.deepcopy(record)
                changed["checks"][1]["observed"] = explanation
                self.audit_record(changed, criteria, ok=False)
        missing = copy.deepcopy(record)
        del missing["checks"][1]["observed"]
        self.audit_record(missing, criteria, ok=False)
        for run_status in ("passed", "partial", "blocked", "failed"):
            for required in (True, None):
                with self.subTest(run_status=run_status, required=required):
                    changed = copy.deepcopy(record)
                    changed["status"] = run_status
                    frozen = copy.deepcopy(criteria)
                    if required is None:
                        del frozen["checks"][1]["required"]  # Defaults to required.
                    else:
                        frozen["checks"][1]["required"] = required
                    self.audit_record(changed, frozen, ok=False)
        # Optionality does not bypass normal frozen-value or evidence validation.
        for field, value in (("expected", "Changed"), ("method", "Changed"),
                             ("evidence", ["missing-evidence.txt"])):
            changed = copy.deepcopy(record)
            changed["checks"][1][field] = value
            self.audit_record(changed, criteria, ok=False)

    def test_evidence_and_record_paths_obey_existing_boundary(self):
        outside = self.base / "outside.txt"
        outside.write_text("outside")
        (self.project / "escape.txt").symlink_to(outside)
        for evidence in ("missing.txt", "../outside.txt", str(outside), "escape.txt", ".env",
                         "http://example.com/result", "https://example.com/result?secret=x",
                         "https://" + "fixture" + ":" + "secret" + "@example.com/result", "https://example.com/result#fragment"):
            with self.subTest(evidence=evidence):
                changed = copy.deepcopy(self.record)
                changed["checks"][0]["evidence"] = [evidence]
                self.audit_record(changed, ok=False)
        self.audit_record(ok=False, record_path="../outside.txt")
        self.audit_record(ok=False, record_path="escape.txt")
        self.audit_record(ok=False, record_path=str(outside))

    def test_malformed_json_and_container_types(self):
        for record in ([], None, {"status": "passed", "checks": {}},
                       {"status": "passed", "checks": [False]}):
            # None is written explicitly; the utility normally uses it for the default.
            if record is None:
                (self.project / "null-record.json").write_text("null")
                self.audit_record(ok=False, record_path="null-record.json")
            else:
                self.audit_record(record=record, ok=False)
        for field, value in (("evidence", "evidence.txt"), ("evidence", [0]), ("id", [])):
            changed = copy.deepcopy(self.record)
            changed["checks"][0][field] = value
            self.audit_record(changed, ok=False)
        for criteria in ([], {"checks": {}}, {"checks": [0]},
                         {"checks": [{"id": "check-01", "expected": 0, "method": False}]},
                         {"checks": [{"id": "check-01", "expected": 0, "method": "Oracle", "required": 1}]}):
            self.audit_record(criteria=criteria, ok=False)
        for content in ("{", '{"status":"passed","checks":NaN}',
                        '{"status":"passed","checks":[{"id":"check-01","expected":0,"method":"Compare source sum","status":"pass","evidence":["evidence.txt"],"observed":1e999}]}'):
            (self.project / "malformed.json").write_text(content)
            self.audit_record(ok=False, record_path="malformed.json")


if __name__ == "__main__":
    unittest.main()
