"""Parent-only reservation, native observation, release and integration for this task."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from common import FIELDS, ROOT, ROLES, RUNS, binding, digest, identity, project_file, read_json, require, reservation, save_json, utc

ACTIVE = {'reserved', 'dispatched', 'running', 'pending'}
LIMITS = {'max_attempts': 5, 'max_workers': 2, 'max_concurrency': 2, 'max_depth': 1}


def evidence(relative):
    path = project_file(relative)
    require(path.is_file(), 'observation evidence must be an existing local file')
    return {'path': relative, 'sha256': digest(path.read_bytes())}


def event(ledger, item, action, **details):
    ledger['events'].append(dict(at=utc(), reservation_id=item['reservation_id'], action=action, **details))


def reserve(args, ledger):
    configured = read_json(project_file('agent.json'))['bounds']
    for name, ceiling in LIMITS.items():
        value = configured[name]
        require(type(value) is int and 0 <= value <= ceiling, f'invalid {name}')
        require(value > 0, f'{name} is zero')
    require(type(configured['max_cost_usd']) in (int, float) and configured['max_cost_usd'] == 0,
            'this task has zero API budget')
    require(args.depth == 1 and args.depth <= configured['max_depth'], 'child depth must be 1')
    items = ledger['reservations']
    require(len(items) < configured['max_attempts'], 'cumulative dispatch budget exhausted')
    active = [item for item in items if item['state'] in ACTIVE]
    require(len(active) < configured['max_concurrency'], 'active-child cap reached; reconcile existing handles')
    if ledger['started_at']:
        elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(ledger['started_at'])
        require(elapsed.total_seconds() < 20 * 60, 'overall case time bound reached')
    bound = binding(args.run_id, args.role)
    require(all((item['binding']['run_id'], item['binding']['role']) != (args.run_id, args.role) for item in items),
            'run/role already reserved; reconcile original reservation')
    require(bool(args.worker.strip()), 'worker identity must be nonempty')
    workers = {item['worker_id'] for item in items}
    require(args.worker in workers or len(workers) < configured['max_workers'], 'unique-worker cap reached')
    for prior in items:
        require((prior['binding']['role'] == args.role) == (prior['worker_id'] == args.worker),
                'worker identity must stay with its assigned role')
    require(all(item['worker_id'] != args.worker for item in active), 'worker already has an active assignment')
    if args.run_id == 'primary':
        probe = [item for item in items if item['binding']['run_id'] == 'probe']
        require(len(probe) == 1 and probe[0]['state'] == 'completed', 'finish and reconcile the missing-field probe first')
        probe_result = read_json(project_file(probe[0]['binding']['result_path']))
        require(all(probe_result.get(k) == v for k, v in identity(probe[0]).items()) and
                probe_result.get('source_sha256') == probe[0]['binding']['source_sha256'] and
                probe_result.get('validation_outcome') == 'invalid', 'missing-field probe requires its bound invalid result')
    if args.run_id == 'followup':
        require(project_file('runs/primary/integration.json').is_file(), 'integrate the primary run before the saved follow-up')
    require(digest(project_file(bound['source_path']).read_bytes()) == bound['source_sha256'], 'source has changed since binding')
    for name in ('result_path', 'ready_path'):
        require(not project_file(bound[name]).exists(), f'{name} already exists')
    item = {'reservation_id': f'd{len(items) + 1:02}', 'worker_id': args.worker, 'binding': bound,
            'depth': args.depth, 'state': 'reserved', 'native_handle': None, 'native_status': None}
    if not ledger['started_at']:
        ledger['started_at'] = utc()
    items.append(item)
    event(ledger, item, 'reserve', binding=bound, worker_id=args.worker, active_before=len(active))
    save_json(project_file('budget.json'), ledger, replace=True)
    return item


def attach(args, ledger):
    item = reservation(ledger, args.reservation_id)
    require(item['state'] in ('reserved', 'pending') and item['native_handle'] is None, 'reservation already attached or ended')
    require(bool(args.handle.strip()) and args.handle != '-', 'attach requires the actual native handle')
    require(all(other['native_handle'] != args.handle or other['state'] not in ACTIVE for other in ledger['reservations']),
            'native handle already active')
    observed = evidence(args.evidence)
    item.update(state='dispatched', native_handle=args.handle)
    event(ledger, item, 'attach', native_handle=args.handle, evidence=observed)
    save_json(project_file('budget.json'), ledger, replace=True)
    return item


def observe(args, ledger):
    item = reservation(ledger, args.reservation_id)
    require(item['state'] in ACTIVE, 'terminal reservations remain immutable')
    attached = item['native_handle']
    require((attached is not None and args.handle == attached) or
            (attached is None and args.handle == '-' and args.status == 'pending'), 'observation must use the original native handle')
    observed = evidence(args.evidence)
    item['state'] = args.status
    if args.status != 'pending':
        item['native_status'] = args.status
    event(ledger, item, 'observe', state=args.status, native_handle=attached, evidence=observed)
    save_json(project_file('budget.json'), ledger, replace=True)
    return item


def children(ledger, run_id):
    matching = {item['binding']['role']: item for item in ledger['reservations'] if item['binding']['run_id'] == run_id}
    require(set(matching) == set(ROLES), 'run requires both child reservations')
    return matching


def require_identity(record, item):
    bound = item['binding']
    require(bound == binding(bound['run_id'], bound['role']), 'saved run binding differs from reservation')
    fields = dict(identity(item), **{field: bound[field] for field in ('run_id', 'role', 'source_path', 'source_sha256')})
    require(all(record.get(key) == value for key, value in fields.items()), 'artifact does not match full immutable assignment identity')
    require(digest(project_file(bound['source_path']).read_bytes()) == bound['source_sha256'], 'bound source bytes changed')


def release(args, ledger):
    require(args.run_id == 'primary', 'only primary uses a release gate')
    gate = project_file(f'runs/{args.run_id}/release.json')
    require(not gate.exists(), 'release gate already exists')
    snapshot = evidence(args.evidence)
    current = children(ledger, args.run_id)
    ready_refs = {}
    pids = set()
    for role, item in current.items():
        require(item['state'] in ('running', 'pending') and item['native_status'] == 'running' and item['native_handle'],
                'parent must first record both original handles observed running')
        bound = item['binding']
        require(not project_file(bound['result_path']).exists(), 'child already has final tool output; do not release')
        raw = project_file(bound['ready_path']).read_bytes()
        ready = json.loads(raw)
        require_identity(ready, item)
        require(ready['validation_outcome'] == 'ready_pending_release', 'expected a source-validated pending ready receipt')
        require(ready['process_start_monotonic_ns'] <= ready['source_read_monotonic_ns'] <=
                ready['ready_monotonic_ns'] <= time.monotonic_ns() < ready['deadline_monotonic_ns'], 'ready interval is invalid or expired')
        pid = ready['pid']
        require(type(pid) is int and pid > 0 and pid not in pids, 'expected separate positive process IDs')
        os.kill(pid, 0)
        pids.add(pid)
        ready_refs[role] = {'reservation_id': item['reservation_id'], 'ready_sha256': digest(raw)}
    value = {'run_id': args.run_id, 'released_at_utc': utc(), 'released_monotonic_ns': time.monotonic_ns(),
             'native_running_snapshot': snapshot, 'children': ready_refs}
    save_json(gate, value)
    return value


def verify_result(item, override=None):
    require(item['state'] == 'completed' and item['native_handle'], 'authoritative native completion required before integration')
    path = override or item['binding']['result_path']
    raw = project_file(path).read_bytes()
    result = json.loads(raw)
    require_identity(result, item)
    require(result.get('validation_outcome') == 'valid', 'child result is not valid')
    require(type(result.get('normalized_rows')) is list and all(type(row) is dict and set(row) == set(FIELDS) for row in result['normalized_rows']),
            'child result is missing normalized rows')
    rows = result['normalized_rows']
    require(all(type(row['sku']) is str and row['sku'].strip() and
                all(type(row[key]) is int and row[key] >= 0 for key in FIELDS[1:]) for row in rows),
            'child rows contain invalid types or values')
    require(len({row['sku'] for row in rows}) == len(rows), 'child rows contain duplicate SKUs')
    require(all(type(result.get(key)) is int and result[key] >= 0 for key in ('units_total', 'cost_cents_total')),
            'child result is missing nonnegative integer totals')
    return result, {'path': path, 'sha256': digest(raw)}


def integrate(args, ledger):
    require(args.run_id in ('primary', 'followup'), 'invalid integration run')
    output = project_file(f'runs/{args.run_id}/integration.json')
    require(not output.exists(), 'run already integrated; inspect its receipt')
    oracle_path = args.oracle.resolve(strict=True)
    require(ROOT not in oracle_path.parents, 'independent oracle must be supplied from outside the generated package')
    raw = oracle_path.read_bytes()
    oracle = json.loads(raw)
    require(oracle['run_id'] == args.run_id, 'oracle run identity mismatch')
    results, refs = {}, {}
    for role, item in children(ledger, args.run_id).items():
        result, ref = verify_result(item)
        comparable = {key: result[key] for key in ('source_path', 'source_sha256', 'normalized_rows', 'units_total', 'cost_cents_total')}
        require(comparable == oracle['children'][role], f'child {role} differs from parent independent oracle')
        results[role] = comparable
        refs[role] = dict(ref, reservation_id=item['reservation_id'], native_handle=item['native_handle'])
    a, b = results['A'], results['B']
    au, bu = a['units_total'], b['units_total']
    ac, bc = a['cost_cents_total'], b['cost_cents_total']
    left, right = ac * bu, bc * au
    lower = ('tie' if left == right else 'A' if left < right else 'B') if au and bu else ('A' if au else 'B' if bu else 'neither_eligible')
    result = {'run_id': args.run_id, 'integrated_at_utc': utc(), 'oracle_sha256': digest(raw), 'child_results': refs,
              'children': results, 'combined_units': au + bu, 'combined_cost_cents': ac + bc,
              'cost_per_unit_comparison': {'lower_cost_role': lower, 'ineligible_roles': [role for role in ROLES if not results[role]['units_total']],
                                           'A_cost_times_B_units': left if au and bu else None,
                                           'B_cost_times_A_units': right if au and bu else None}}
    save_json(output, result)
    return result


def reindex():
    index = read_json(project_file('toolbox/index.json'))
    locations = {resource['location'] for resource in index['resources']}
    for path in sorted((ROOT / 'runs').rglob('*')):
        if not path.is_file() or path.name.startswith('.'):
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in locations:
            continue
        resource_id = 'run-' + relative.removeprefix('runs/').removesuffix('.json').lower().replace('/', '-').replace('_', '-').replace('.', '-')
        require(all(entry['id'] != resource_id for entry in index['resources']), f'index ID collision: {relative}')
        index['resources'].append({'id': resource_id, 'purpose': 'Run artifact ' + relative, 'kind': 'evidence',
                                   'location': relative, 'version': digest(path.read_bytes()),
                                   'input_contract': 'Run-bound local artifact', 'output_contract': 'Stored result or observation for independent review',
                                   'dependencies': [], 'status': 'draft', 'used_by': ['step-04'],
                                   'validation': {'method': 'Indexed for independent review', 'evidence': []},
                                   'replaces': None, 'reuse_decision': 'Distinct run evidence preserves historical artifacts'})
    save_json(project_file('toolbox/index.json'), index, replace=True)
    return {'resources': len(index['resources'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('reserve')
    command.add_argument('run_id', choices=RUNS)
    command.add_argument('role', choices=ROLES)
    command.add_argument('worker')
    command.add_argument('--depth', type=int, default=1)
    for name in ('attach', 'observe'):
        command = commands.add_parser(name)
        command.add_argument('reservation_id')
        command.add_argument('handle')
        if name == 'observe':
            command.add_argument('status', choices=('running', 'pending', 'completed', 'failed', 'cancelled'))
        command.add_argument('evidence')
    command = commands.add_parser('release')
    command.add_argument('run_id', choices=RUNS)
    command.add_argument('evidence')
    command = commands.add_parser('verify-result')
    command.add_argument('reservation_id')
    command.add_argument('--result')
    command = commands.add_parser('integrate')
    command.add_argument('run_id', choices=('primary', 'followup'))
    command.add_argument('--oracle', type=Path, required=True)
    commands.add_parser('index')
    commands.add_parser('status')
    args = parser.parse_args()
    try:
        ledger = read_json(project_file('budget.json'))
        actions = {'reserve': reserve, 'attach': attach, 'observe': observe, 'release': release, 'integrate': integrate}
        if args.command in actions:
            result = actions[args.command](args, ledger)
        elif args.command == 'verify-result':
            result, ref = verify_result(reservation(ledger, args.reservation_id), args.result)
            result = {'artifact': ref, 'result': result}
        elif args.command == 'index':
            result = reindex()
        else:
            result = ledger
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'ok': False, 'command': args.command, 'reason': str(error)}))
        return 1
    print(json.dumps({'ok': True, 'command': args.command, 'result': result}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
