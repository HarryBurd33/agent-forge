"""Replay a generated runner regression against a separate local provider process."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'recovery'
IDENTITY = {'key': 'op-17', 'action': 'deliver', 'target': 'local-outbox-blue',
            'payload_sha256': hashlib.sha256(b'{"total":13}').hexdigest(), 'source_version': 'rows-v2'}


class RecoveryWorkflow(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runner = self.root / 'runner.py'
        source = (FIXTURES / 'runner.py').read_text()
        if os.environ.get('AGENT_FORGE_TEST_LEGACY_GUARD') == '1':
            old_guard = 'state["outcome"] not in {"uncertain", "still_unknown"}'
            self.assertEqual(source.count(old_guard), 1)
            source = source.replace(old_guard, 'state["outcome"] != "uncertain"')
        self.runner.write_text(source)
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                        AGENT_FORGE_TEST_PROVIDER=str(FIXTURES / 'provider.py'),
                        AGENT_FORGE_TEST_PROVIDER_STATE=str(self.root / 'provider-state'))

    def call(self, file, *args, expected=0):
        result = subprocess.run([sys.executable, str(file), *args], cwd=self.root,
                                env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def provider(self, command, case, *args):
        return json.loads(self.call(FIXTURES / 'provider_setup.py', command, '--case', case, *args).stdout)

    def run_case(self, case, mode='recover', expected=0):
        result = self.call(self.runner, case, mode, expected=expected)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def state(self, case):
        return json.loads((self.root / (case + '.json')).read_text())

    def assert_ledger(self, case, commands, effect_origins):
        ledger = self.provider('inspect', case)
        self.assertEqual([x['command'] for x in ledger['calls']], commands)
        self.assertEqual([x['origin'] for x in ledger['effects']], effect_origins)
        return ledger

    def test_lost_ack_commit_and_distinct_process_readback(self):
        self.provider('init', 'lost_ack')
        first = self.run_case('lost_ack', 'start', expected=75)
        self.assertEqual(first['outcome'], 'uncertain')
        saved = self.state('lost_ack')
        self.assertEqual(saved['intent'], IDENTITY)
        event = saved['calls'][0]
        self.assertEqual((event['exit_code'], event['stdout']), (75, ''))
        ledger = self.assert_ledger('lost_ack', ['send'], ['send'])
        self.assertEqual(ledger['calls'][0]['outcome'], 'committed_ack_lost')
        self.assertEqual(json.loads(ledger['effects'][0]['identity']), IDENTITY)
        self.assertLessEqual(saved['intent_saved_at'], ledger['effects'][0]['at'])
        recovered = self.run_case('lost_ack')
        self.assertEqual(recovered['outcome'], 'reconciled_prior_commit')
        self.assertNotEqual(first['runner_pid'], recovered['runner_pid'])
        self.assertEqual(recovered['detail']['receipt'], ledger['effects'][0]['receipt'])
        self.assert_ledger('lost_ack', ['send', 'lookup'], ['send'])

    def test_target_and_payload_conflicts_prevent_send_or_recovery(self):
        for overrides, field in ((('--conflict-total', '13'), 'target'),
                                 (('--conflict-target', 'local-outbox-blue'), 'payload_sha256')):
            with self.subTest(field=field):
                self.provider('init', 'conflict', '--reset', *overrides)
                result = self.run_case('conflict')
                self.assertEqual(result['outcome'], 'identity_conflict')
                self.assertEqual(result['detail']['mismatched_fields'], [field])
                self.assertEqual(self.state('conflict')['intent'], IDENTITY)
                self.assertIn('does not authorize', self.run_case('conflict', expected=1))
                self.assert_ledger('conflict', ['lookup'], ['seed'])
                (self.root / 'conflict.json').unlink()

    def test_unknown_later_resolution(self):
        self.provider('init', 'unknown')
        pending = self.run_case('unknown')
        self.assertEqual(pending['outcome'], 'still_unknown')
        saved = self.state('unknown')
        self.assert_ledger('unknown', ['lookup'], [])
        resolution = self.provider('resolve', 'unknown')
        recovered = self.run_case('unknown')
        self.assertEqual(recovered['outcome'], 'reconciled_prior_commit')
        self.assertNotEqual(pending['runner_pid'], recovered['runner_pid'])
        self.assertEqual(recovered['detail']['receipt'], resolution['receipt'])
        final = self.state('unknown')
        self.assertEqual(final['intent'], saved['intent'])
        self.assertEqual(final['calls'][:1], saved['calls'])
        self.assertEqual(len(final['calls']), 2)
        self.assert_ledger('unknown', ['lookup', 'lookup'], ['later_resolution'])

    def test_exhausted_budget_prevents_additional_lookup(self):
        self.provider('init', 'unknown')
        for _ in range(3):
            self.assertEqual(self.run_case('unknown')['outcome'], 'still_unknown')
        self.provider('resolve', 'unknown')
        self.assertIn('provider call limit reached', self.run_case('unknown', expected=1))
        self.assertEqual(len(self.state('unknown')['calls']), 3)
        self.assert_ledger('unknown', ['lookup'] * 3, ['later_resolution'])

    def test_unavailable_lookup_preserves_pending_intent(self):
        self.assertIn('Lookup unavailable', self.run_case('unknown', expected=1)['detail'])
        state = self.state('unknown')
        self.assertEqual(state['outcome'], 'uncertain')
        self.assertEqual(state['intent'], IDENTITY)
        self.assertEqual(len(state['calls']), 1)
        self.assertEqual(state['calls'][0]['exit_code'], 69)
        self.assertFalse((self.root / 'provider-state').exists())

    def test_terminal_noncommit_uses_same_identity_and_matching_acknowledgement(self):
        self.provider('init', 'not_committed')
        result = self.run_case('not_committed')
        self.assertEqual(result['outcome'], 'verified_delivered')
        self.assertEqual(result['detail']['evidence'], 'matching provider acknowledgement')
        ledger = self.assert_ledger('not_committed', ['lookup', 'send'], ['send'])
        self.assertEqual(json.loads(ledger['effects'][0]['identity']), IDENTITY)
        self.assertEqual(result['detail']['receipt'], ledger['effects'][0]['receipt'])


if __name__ == '__main__':
    unittest.main()
