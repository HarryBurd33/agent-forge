"""Local file operations for the fixed source-audit qualification."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
RUNS = ('probe', 'primary', 'followup')
ROLES = ('A', 'B')
FIELDS = ('sku', 'units', 'unit_cost_cents')


class Refused(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Refused(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def project_file(relative):
    path = Path(relative)
    require(not path.is_absolute() and path.parts and '..' not in path.parts, 'expected a project-relative path')
    current = ROOT
    for component in path.parts:
        current = current / component
        require(not current.is_symlink(), f'symlink refused: {relative}')
    return current


def read_json(path):
    return json.loads(path.read_bytes())


def save_json(path, value, *, replace=False):
    with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as output:
        temp = Path(output.name)
        try:
            json.dump(value, output, indent=2, ensure_ascii=False)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        if replace:
            os.replace(temp, path)
        else:
            os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def binding(run_id, role):
    require(run_id in RUNS and role in ROLES, 'unknown run or role')
    require(run_id != 'probe' or role == 'B', 'only B is assigned to the missing-field probe')
    path = project_file(f'bindings/{run_id}.json')
    data = read_json(path)
    suffix = 'csv' if role == 'A' else 'json'
    output_dir = f'runs/{run_id}/child-{role}'
    result = data['children'][role]
    fixed = {'run_id': run_id, 'role': role, 'format': suffix,
             'source_path': f'inputs/{run_id}/{role.lower()}.{suffix}',
             'output_dir': output_dir, 'ready_path': f'{output_dir}/ready.json',
             'result_path': f'{output_dir}/result.json',
             'gate_path': f'runs/{run_id}/release.json' if run_id == 'primary' else None,
             'barrier_timeout_seconds': 60 if run_id == 'primary' else 0}
    require(all(result.get(key) == value for key, value in fixed.items()), 'run binding paths or policy differ from the task contract')
    require(len(result['source_sha256']) == 64 and all(c in '0123456789abcdef' for c in result['source_sha256']), 'invalid source digest')
    return result


def reservation(ledger, reservation_id):
    matching = [item for item in ledger['reservations'] if item['reservation_id'] == reservation_id]
    require(len(matching) == 1, 'unknown or duplicate reservation identity')
    return matching[0]


def identity(item):
    return {key: item[key] for key in ('reservation_id', 'worker_id', 'binding')}
