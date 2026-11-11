"""Exercise the generated parallel task protocol with local Python processes.

All recorded host observations are synthetic local test fixtures. Child source
reads, process lifetimes, guard commands and artifacts are real subprocess work.
"""
import csv
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'parallel'
FIELDS = ('sku', 'units', 'unit_cost_cents')
ROWS = {
    ('primary', 'A'): [('a1', 3, 125), ('a2', 0, 999), ('a3', 2, 240)],
    ('primary', 'B'): [('b1', 4, 210), ('b2', 1, 0), ('b3', 2, 115)],
    ('followup', 'A'): [('a1', 1, 125), ('a2', 0, 999), ('a3', 4, 240)],
    ('followup', 'B'): [('b1', 4, 500), ('b2', 1, 0), ('b3', 2, 450)],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def read_json(path):
    return json.loads(path.read_bytes())


def inventory(root):
    return {path.relative_to(root).as_posix(): sha(path) for path in root.rglob('*') if path.is_file()}


def create_task(root):
    shutil.copytree(FIXTURES, root / 'tools')
    write_json(root / 'agent.json', {'bounds': {'max_attempts': 5, 'max_minutes': 20, 'max_depth': 1,
               'max_concurrency': 2, 'max_workers': 2, 'max_cost_usd': 0}})
    write_json(root / 'budget.json', {'schema_version': 1, 'started_at': None, 'reservations': [], 'events': []})
    write_json(root / 'toolbox/index.json', {'schema_version': 1, 'project_id': 'local-parallel-test', 'resources': []})
    for run in ('probe', 'primary', 'followup'):
        bindings = {}
        for role in ('B',) if run == 'probe' else ('A', 'B'):
            records = [dict(zip(FIELDS, row)) for row in ROWS[('primary' if run == 'probe' else run, role)]]
            if run == 'probe':
                records[-1].pop('unit_cost_cents')
            source_format = 'csv' if role == 'A' else 'json'
            source_path = f'inputs/{run}/{role.lower()}.{source_format}'
            source = root / source_path
            source.parent.mkdir(parents=True, exist_ok=True)
            if source_format == 'csv':
                with source.open('w', newline='', encoding='utf-8') as stream:
                    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
                    writer.writeheader()
                    writer.writerows(records)
            else:
                write_json(source, {'lines': records})
            destination = f'runs/{run}/child-{role}'
            (root / destination).mkdir(parents=True)
            bindings[role] = {'run_id': run, 'role': role, 'format': source_format,
                              'source_path': source_path, 'source_sha256': sha(source),
                              'output_dir': destination, 'ready_path': destination + '/ready.json',
                              'result_path': destination + '/result.json',
                              'gate_path': f'runs/{run}/release.json' if run == 'primary' else None,
                              'barrier_timeout_seconds': 60 if run == 'primary' else 0}
        write_json(root / 'bindings' / (run + '.json'), {'run_id': run, 'children': bindings})


def independent_oracle(root, run):
    """Read actual raw sources with a separate parser and exact integer arithmetic."""
    children = {}
    for role, extension in (('A', 'csv'), ('B', 'json')):
        relative = f'inputs/{run}/{role.lower()}.{extension}'
        source = root / relative
        if extension == 'csv':
            raw = csv.reader(io.StringIO(source.read_text(encoding='utf-8')))
            assert tuple(next(raw)) == FIELDS
            rows = [{'sku': sku, 'units': int(units), 'unit_cost_cents': int(cost)} for sku, units, cost in raw]
        else:
            rows = read_json(source)['lines']
        children[role] = {'source_path': relative, 'source_sha256': sha(source), 'normalized_rows': rows,
                          'units_total': sum(row['units'] for row in rows),
                          'cost_cents_total': sum(row['units'] * row['unit_cost_cents'] for row in rows)}
    return {'run_id': run, 'children': children}


class ParallelWorkflow(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / 'package'
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        create_task(self.root)
        if os.environ.get('AGENT_FORGE_TEST_WEAKEN_ACTIVE_CAP') == '1':
            fixture = self.root / 'tools/parent.py'
            source = fixture.read_text(encoding='utf-8')
            guard = "require(len(active) < configured['max_concurrency'],"
            self.assertEqual(source.count(guard), 1)
            fixture.write_text(source.replace(guard, "require(len(active) <= configured['max_concurrency'],"), encoding='utf-8')

    def parent(self, *args, expected=0, root=None):
        directory = root or self.root
        result = subprocess.run([sys.executable, 'tools/parent.py', *map(str, args)], cwd=directory,
                                env=self.env, capture_output=True, text=True, timeout=12)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def reject(self, *args, reason, root=None):
        directory = root or self.root
        before = sha(directory / 'budget.json')
        result = self.parent(*args, expected=1, root=directory)
        self.assertIn(reason, result['reason'])
        self.assertEqual(before, sha(directory / 'budget.json'))
        return result

    def bound(self, run, role):
        return read_json(self.root / 'bindings' / (run + '.json'))['children'][role]

    def reserve(self, run, role):
        return self.parent('reserve', run, role, 'fixture-worker-' + role)['result']

    def local_evidence(self, run, name, **observations):
        path = f'runs/{run}/local-evidence/{name}.json'
        write_json(self.root / path, {'evidence_kind': 'synthetic_local_fixture',
                   'observed_at': datetime.now(timezone.utc).isoformat(), **observations})
        return path

    def start_child(self, item):
        bound = item['binding']
        process = subprocess.Popen([sys.executable, 'tools/child.py', bound['run_id'], bound['role'], item['reservation_id']],
                                   cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.close_process, process)
        evidence = self.local_evidence(bound['run_id'], bound['role'] + '-attach', local_pid=process.pid)
        self.parent('attach', item['reservation_id'], 'fixture-handle-' + bound['role'], evidence)
        return process

    @staticmethod
    def close_process(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def observe(self, item, state, **observations):
        bound = item['binding']
        role = bound['role']
        evidence = self.local_evidence(bound['run_id'], role + '-' + state, **observations)
        return self.parent('observe', item['reservation_id'], 'fixture-handle-' + role, state, evidence)['result']

    def finish_child(self, item, process, expected):
        stdout, stderr = process.communicate(timeout=12)
        self.assertEqual(process.returncode, expected, stdout + stderr)
        result = read_json(self.root / item['binding']['result_path'])
        self.assertEqual(result['pid'], process.pid)
        self.assertEqual(result['binding'], item['binding'])
        self.assertEqual(result['source_sha256'], item['binding']['source_sha256'])
        self.observe(item, 'completed', local_pid=process.pid, local_exit=process.returncode)
        return result

    def wait_ready(self, item, process):
        path = self.root / item['binding']['ready_path']
        deadline = time.monotonic() + 12
        while not path.is_file() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(path.is_file(), 'child did not create its ready receipt')
        ready = read_json(path)
        self.assertIsNone(process.poll())
        self.assertFalse((self.root / item['binding']['result_path']).exists())
        self.assertEqual(ready['validation_outcome'], 'ready_pending_release')
        self.assertEqual(ready['pid'], process.pid)
        self.assertEqual(ready['source_sha256'], item['binding']['source_sha256'])
        self.assertLessEqual(ready['source_read_monotonic_ns'], ready['ready_monotonic_ns'])
        self.assertEqual(ready['deadline_monotonic_ns'] - ready['ready_monotonic_ns'], 60 * 10**9)
        return ready

    def run_probe(self):
        item = self.reserve('probe', 'B')
        result = self.finish_child(item, self.start_child(item), 65)
        self.assertEqual(result['validation_outcome'], 'invalid')
        self.assertIn('row 3 (b3): missing unit_cost_cents', result['error'])
        self.assertFalse({'normalized_rows', 'units_total', 'cost_cents_total'} & result.keys())
        return result

    def run_primary(self, exercise_guards=False):
        self.run_probe()
        item_a = self.reserve('primary', 'A')
        process_a = self.start_child(item_a)
        ready_a = self.wait_ready(item_a, process_a)
        self.observe(item_a, 'running', local_pid=process_a.pid)
        if exercise_guards:
            pending = self.observe(item_a, 'pending', local_pid=process_a.pid, final_result_present=False)
            self.assertEqual(pending['native_handle'], 'fixture-handle-A')
            self.assertEqual(pending['binding'], item_a['binding'])
            self.reject('reserve', 'primary', 'A', 'fixture-worker-A', reason='already reserved')
            self.reject('observe', item_a['reservation_id'], 'wrong-local-handle', 'completed',
                        'runs/primary/local-evidence/A-pending.json', reason='original native handle')
            control = self.base / 'cap-one'
            shutil.copytree(self.root, control)
            config = read_json(control / 'agent.json')
            config['bounds']['max_concurrency'] = 1
            write_json(control / 'agent.json', config)
            self.reject('reserve', 'primary', 'B', 'fixture-worker-B', root=control, reason='active-child cap reached')
        item_b = self.reserve('primary', 'B')
        process_b = self.start_child(item_b)
        ready_b = self.wait_ready(item_b, process_b)
        self.observe(item_b, 'running', local_pid=process_b.pid)
        if exercise_guards:
            self.reject('reserve', 'followup', 'A', 'fixture-worker-A', reason='active-child cap reached')
        self.assertIsNone(process_a.poll())
        self.assertIsNone(process_b.poll())
        self.assertNotEqual(process_a.pid, process_b.pid)
        evidence = self.local_evidence('primary', 'both-ready', local_pids=[process_a.pid, process_b.pid])
        self.parent('release', 'primary', evidence)
        gate = self.root / 'runs/primary/release.json'
        gate_receipt = read_json(gate)
        self.assertEqual(gate_receipt['native_running_snapshot']['sha256'], sha(self.root / evidence))
        for item in (item_a, item_b):
            bound = item['binding']
            self.assertEqual(gate_receipt['children'][bound['role']],
                             {'reservation_id': item['reservation_id'], 'ready_sha256': sha(self.root / bound['ready_path'])})
        result_a = self.finish_child(item_a, process_a, 0)
        result_b = self.finish_child(item_b, process_b, 0)
        latest_ready = max(ready_a['ready_monotonic_ns'], ready_b['ready_monotonic_ns'])
        earliest_end = min(result_a['process_end_monotonic_ns'], result_b['process_end_monotonic_ns'])
        self.assertLess(latest_ready, earliest_end)
        for result in (result_a, result_b):
            self.assertEqual(result['release_sha256'], sha(gate))
        return item_a, result_a, result_b

    def integrate(self, run):
        oracle = independent_oracle(self.root, run)
        path = self.base / (run + '-oracle.json')
        write_json(path, oracle)
        result = self.parent('integrate', run, '--oracle', path)['result']
        self.assertEqual(result['oracle_sha256'], sha(path))
        self.assertEqual(result['children'], oracle['children'])
        self.assertEqual(result['combined_units'], sum(item['units_total'] for item in oracle['children'].values()))
        self.assertEqual(result['combined_cost_cents'], sum(item['cost_cents_total'] for item in oracle['children'].values()))
        costs = {role: Fraction(item['cost_cents_total'], item['units_total']) for role, item in oracle['children'].items()}
        lower = 'tie' if costs['A'] == costs['B'] else min(costs, key=costs.get)
        self.assertEqual(result['cost_per_unit_comparison']['lower_cost_role'], lower)
        return result

    def test_zero_and_depth_refusals_leave_ledger_unchanged(self):
        path = self.root / 'agent.json'
        original = read_json(path)
        for bound in ('max_depth', 'max_concurrency', 'max_workers'):
            with self.subTest(bound=bound):
                config = {'bounds': dict(original['bounds'], **{bound: 0})}
                write_json(path, config)
                self.reject('reserve', 'probe', 'B', 'fixture-worker-B', reason=bound + ' is zero')
        write_json(path, original)
        self.reject('reserve', 'probe', 'B', 'fixture-worker-B', '--depth', 2, reason='depth must be 1')
        self.assertEqual(read_json(self.root / 'budget.json')['reservations'], [])

    def test_missing_field_stops_without_totals_and_spends_one_reservation(self):
        before = inventory(self.root / 'inputs')
        result = self.run_probe()
        self.assertEqual(result['format_observations']['source_format'], 'json')
        self.assertEqual(before, inventory(self.root / 'inputs'))
        self.assertEqual(len(read_json(self.root / 'budget.json')['reservations']), 1)
        self.reject('reserve', 'probe', 'B', 'fixture-worker-B', reason='already reserved')

    @unittest.skipUnless(os.name == 'posix', 'fixture release uses POSIX process liveness')
    def test_overlap_active_caps_and_pending_handle(self):
        item, a, b = self.run_primary(exercise_guards=True)
        self.assertEqual(a['format_observations']['zero_units_rows'], 1)
        self.assertEqual(b['format_observations']['zero_unit_cost_rows'], 1)
        self.assertIn({'sku': 'a2', 'units': 0, 'unit_cost_cents': 999}, a['normalized_rows'])
        self.assertIn({'sku': 'b2', 'units': 1, 'unit_cost_cents': 0}, b['normalized_rows'])
        ledger = read_json(self.root / 'budget.json')
        self.assertEqual(len(ledger['reservations']), 3)
        status_events = [event['state'] for event in ledger['events'] if event['reservation_id'] == item['reservation_id'] and event['action'] == 'observe']
        self.assertEqual(status_events, ['running', 'pending', 'completed'])
        self.integrate('primary')

    @unittest.skipUnless(os.name == 'posix', 'fixture release uses POSIX process liveness')
    def test_mismatched_result_refused_and_integration_written_once(self):
        item, result, _ = self.run_primary()
        bound_result = self.root / item['binding']['result_path']
        original = sha(bound_result)
        for field, mismatch in (('run_id', 'followup'), ('source_sha256', '0' * 64)):
            with self.subTest(field=field):
                path = f'runs/primary/heldout-{field}.json'
                write_json(self.root / path, dict(result, **{field: mismatch}))
                self.reject('verify-result', item['reservation_id'], '--result', path, reason='full immutable assignment identity')
        self.assertEqual(original, sha(bound_result))
        self.integrate('primary')
        integration = self.root / 'runs/primary/integration.json'
        before = sha(integration)
        self.reject('integrate', 'primary', '--oracle', self.base / 'primary-oracle.json', reason='already integrated')
        self.assertEqual(before, sha(integration))

    @unittest.skipUnless(os.name == 'posix', 'fixture release uses POSIX process liveness')
    def test_followup_reuses_same_budget_and_preserves_primary_history(self):
        self.run_primary()
        primary = self.integrate('primary')
        history = inventory(self.root / 'runs/primary')
        sources = inventory(self.root / 'inputs')
        for role in ('A', 'B'):
            item = self.reserve('followup', role)
            self.assertEqual(item['binding'], self.bound('followup', role))
            self.assertIsNone(item['binding']['gate_path'])
            result = self.finish_child(item, self.start_child(item), 0)
            self.assertNotIn('release_sha256', result)
            self.assertNotEqual(result['source_sha256'], primary['children'][role]['source_sha256'])
        followup = self.integrate('followup')
        self.assertNotEqual(primary['cost_per_unit_comparison']['lower_cost_role'], followup['cost_per_unit_comparison']['lower_cost_role'])
        ledger = read_json(self.root / 'budget.json')
        self.assertEqual(len(ledger['reservations']), 5)
        self.assertEqual({item['worker_id'] for item in ledger['reservations']}, {'fixture-worker-A', 'fixture-worker-B'})
        self.reject('reserve', 'followup', 'A', 'fixture-worker-A', reason='cumulative dispatch budget exhausted')
        self.parent('index')
        locations = {item['location'] for item in read_json(self.root / 'toolbox/index.json')['resources']}
        self.assertEqual(locations, {'runs/' + name for name in inventory(self.root / 'runs')})
        self.assertEqual(history, inventory(self.root / 'runs/primary'))
        self.assertEqual(sources, inventory(self.root / 'inputs'))


if __name__ == '__main__':
    unittest.main()
