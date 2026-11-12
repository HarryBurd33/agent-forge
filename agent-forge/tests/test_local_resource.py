"""Distinct-process checks for the local SQLite counter and receipt."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest


DEFAULT_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "local_resource.py"
SCRIPT = Path(os.environ.get("AGENT_FORGE_RESOURCE_TEST_SCRIPT", DEFAULT_SCRIPT))
COUNTER = {"resource": "test-counter"}


class LocalResourceTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.database = Path(scratch.name) / "resource.sqlite"

    def invoke(self, action, expected=0, **fields):
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--db", str(self.database), action],
            input=json.dumps({**COUNTER, **fields}), text=True, capture_output=True, timeout=8,
        )
        self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
        return json.loads(process.stdout)

    def claim(self, owner, ttl_ms=5000):
        result = self.invoke("claim", owner=owner, ttl_ms=ttl_ms)
        self.assertEqual(result["status"], "claimed")
        return result

    def test_stale_writer_is_rejected_after_expiry_and_new_claim(self):
        first = self.claim("A", ttl_ms=200)
        while time.time_ns() // 1_000_000 < first["expires_at_ms"]:
            time.sleep(0.01)
        second = self.claim("B")
        self.assertGreater(second["token"], first["token"])
        self.assertEqual(self.invoke(
            "apply", owner="A", token=first["token"], operation_key="stale", delta=1000,
        ), {"status": "stale"})
        self.assertEqual(self.invoke("lookup", operation_key="stale", delta=1000), {"status": "unknown"})
        self.assertEqual(self.invoke("read")["value"], 0)
        self.assertEqual(self.invoke(
            "apply", owner="B", token=second["token"], operation_key="current", delta=7,
        )["value"], 7)

    def test_lost_ack_can_be_looked_up_and_replayed_by_a_new_owner(self):
        first = self.claim("A")
        self.invoke("apply", owner="A", token=first["token"], operation_key="stable", delta=4)
        self.invoke("release", owner="A", token=first["token"])
        second = self.claim("B")

        self.assertEqual(self.invoke("lookup", operation_key="stable", delta=4),
                         {"status": "committed", "value": 4, "token": first["token"]})
        self.assertEqual(self.invoke(
            "apply", owner="B", token=second["token"], operation_key="stable", delta=4,
        ), {"status": "replayed", "value": 4, "token": first["token"]})
        self.assertEqual(self.invoke(
            "apply", owner="B", token=second["token"], operation_key="stable", delta=9,
        ), {"status": "conflict"})
        self.assertEqual(self.invoke("lookup", operation_key="stable", delta=9), {"status": "conflict"})
        self.assertEqual(self.invoke("read")["value"], 4)

    def test_invalid_or_missing_read_does_not_create_a_database(self):
        self.assertEqual(self.invoke("claim", expected=2, owner="A", ttl_ms=True)["status"], "error")
        self.assertEqual(self.invoke("claim", expected=2, owner="", ttl_ms=1)["status"], "error")
        self.assertEqual(self.invoke(
            "apply", expected=2, owner="A", token=1, operation_key="op", delta=False,
        )["status"], "error")
        self.assertEqual(self.invoke(
            "apply", expected=2, owner="A", token=True, operation_key="op", delta=1,
        )["status"], "error")
        self.assertEqual(self.invoke("read"), {"status": "unknown"})
        self.assertEqual(self.invoke("lookup", operation_key="op", delta=1), {"status": "unknown"})
        self.assertFalse(self.database.exists())

    def test_waiting_writer_checks_expiry_after_the_write_lock(self):
        first = self.claim("A", ttl_ms=1000)
        with sqlite3.connect(self.database) as locker:
            locker.execute("BEGIN IMMEDIATE")
            command = subprocess.Popen(
                [sys.executable, str(SCRIPT), "--db", str(self.database), "apply"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                assert command.stdin is not None
                command.stdin.write(json.dumps({
                    **COUNTER, "owner": "A", "token": first["token"], "operation_key": "delayed", "delta": 5,
                }))
                command.stdin.close()
                command.stdin = None
                time.sleep(max(0, (first["expires_at_ms"] - time.time_ns() // 1_000_000) / 1000) + 0.05)
                locker.commit()
                output, error = command.communicate(timeout=6)
                self.assertEqual(command.returncode, 0, error)
                self.assertEqual(json.loads(output), {"status": "stale"})
            finally:
                if command.poll() is None:
                    command.kill()
                    command.communicate()
        self.assertEqual(self.invoke("read")["value"], 0)


if __name__ == "__main__":
    unittest.main()
