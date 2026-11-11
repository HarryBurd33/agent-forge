"""Validate an assigned source and write only its reserved child artifacts."""
import argparse
import csv
import io
import json
import os
import re
import time

from common import FIELDS, ROLES, RUNS, binding, digest, identity, project_file, read_json, require, reservation, save_json, utc


def csv_rows(raw):
    rows = csv.DictReader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True)
    require(rows.fieldnames == list(FIELDS), 'CSV header must be sku,units,unit_cost_cents')
    return list(rows)


def json_rows(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result

    data = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    require(type(data) is dict and type(data.get('lines')) is list, 'JSON source must contain a lines array')
    return data['lines']


def normalize(raw, source_format):
    source = csv_rows(raw) if source_format == 'csv' else json_rows(raw)
    result, seen = [], set()
    for index, row in enumerate(source, 1):
        require(type(row) is dict, f'row {index}: expected object')
        require(None not in row, f'row {index}: unexpected CSV cells')
        sku = row.get('sku')
        require(type(sku) is str and bool(sku.strip()), f'row {index}: missing or invalid sku')
        label = f'row {index} ({sku})'
        require(sku not in seen, f'{label}: duplicate sku')
        seen.add(sku)
        line = {'sku': sku}
        for field in FIELDS[1:]:
            require(field in row and row[field] is not None, f'{label}: missing {field}')
            value = row[field]
            if source_format == 'csv':
                require(re.fullmatch(r'[0-9]+', value) is not None, f'{label}: {field} must be a nonnegative integer')
                value = int(value)
            require(type(value) is int and value >= 0, f'{label}: {field} must be a nonnegative integer')
            line[field] = value
        result.append(line)
    return result


def wait_for_release(gate_path, ready_path, item, deadline):
    while time.monotonic_ns() < deadline:
        if gate_path.is_file():
            raw = gate_path.read_bytes()
            gate = json.loads(raw)
            role = item['binding']['role']
            actual = gate['children'].get(role)
            require(gate['run_id'] == item['binding']['run_id'] and actual == {
                'reservation_id': item['reservation_id'], 'ready_sha256': digest(ready_path.read_bytes())}, 'release gate does not bind this ready receipt')
            return digest(raw)
        remaining = (deadline - time.monotonic_ns()) / 1_000_000_000
        if remaining > 0:
            time.sleep(min(0.2, remaining))
    return None


def main():
    started_mono, started_utc = time.monotonic_ns(), utc()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id', choices=RUNS)
    parser.add_argument('role', choices=ROLES)
    parser.add_argument('reservation_id')
    args = parser.parse_args()
    try:
        bound = binding(args.run_id, args.role)
        ledger = read_json(project_file('budget.json'))
        item = reservation(ledger, args.reservation_id)
        require(item['binding'] == bound and item['state'] in ('reserved', 'dispatched', 'running', 'pending'), 'reservation is not active or does not match this assignment')
        result_path = project_file(bound['result_path'])
        ready_path = project_file(bound['ready_path'])
        require(result_path.parent.is_dir(), 'parent must prepare child-owned output directory')
        require(not result_path.exists() and not ready_path.exists(), 'assignment already has artifacts; reconcile rather than repeat')
    except (OSError, ValueError, KeyError) as error:
        print(json.dumps({'validation_outcome': 'refused', 'error': str(error)}))
        return 64

    record = dict(identity(item), run_id=args.run_id, role=args.role, source_path=bound['source_path'],
                  source_sha256=None, pid=os.getpid(), process_start_monotonic_ns=started_mono,
                  process_start_utc=started_utc, format_observations={'source_format': bound['format']})
    status, code = 'valid', 0
    try:
        raw = project_file(bound['source_path']).read_bytes()
        record.update(source_sha256=digest(raw), source_read_monotonic_ns=time.monotonic_ns(), source_read_utc=utc())
        require(record['source_sha256'] == bound['source_sha256'], 'source does not match the immutable binding')
        rows = normalize(raw, bound['format'])
        record['format_observations'].update(row_count=len(rows), sku_unique=True,
                                            zero_units_rows=sum(row['units'] == 0 for row in rows),
                                            zero_unit_cost_rows=sum(row['unit_cost_cents'] == 0 for row in rows))
        if bound['gate_path'] is not None:
            ready_mono = time.monotonic_ns()
            ready = dict(record, validation_outcome='ready_pending_release', ready_monotonic_ns=ready_mono,
                         ready_utc=utc(), deadline_monotonic_ns=ready_mono + bound['barrier_timeout_seconds'] * 10**9)
            save_json(ready_path, ready)
            record.update(ready_monotonic_ns=ready_mono, ready_utc=ready['ready_utc'])
            gate_sha = wait_for_release(project_file(bound['gate_path']), ready_path, item, ready['deadline_monotonic_ns'])
            if gate_sha is None:
                status, code = 'timeout', 75
                record['error'] = 'release absent at deadline; parent must reconcile original native handle'
            else:
                record.update(release_sha256=gate_sha, release_seen_monotonic_ns=time.monotonic_ns(), release_seen_utc=utc())
        if status == 'valid':
            record.update(normalized_rows=rows, units_total=sum(row['units'] for row in rows),
                          cost_cents_total=sum(row['units'] * row['unit_cost_cents'] for row in rows))
    except (OSError, ValueError, csv.Error, KeyError) as error:
        status, code = 'invalid', 65
        record['error'] = str(error)
    record.update(validation_outcome=status, process_end_monotonic_ns=time.monotonic_ns(), process_end_utc=utc())
    try:
        save_json(result_path, record)
    except OSError as error:
        print(json.dumps({'validation_outcome': 'write_error', 'error': str(error)}))
        return 74
    print(json.dumps({'validation_outcome': status, 'result_path': bound['result_path'], 'error': record.get('error')}))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
