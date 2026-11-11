#!/usr/bin/env python3
"""Parent-only initialization and readback of local provider evidence."""
import argparse
import json
import sqlite3

from provider import CASES, SCHEMA, STATE, canonical, make_identity, put_effect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'inspect', 'resolve'))
    parser.add_argument('--case', choices=CASES, required=True)
    parser.add_argument('--reset', action='store_true', help='replace case state, parent only')
    parser.add_argument('--conflict-target', choices=('local-outbox-blue', 'local-outbox-red'))
    parser.add_argument('--conflict-total', type=int)
    args = parser.parse_args()
    if (args.conflict_target is not None or args.conflict_total is not None) and (args.command != 'init' or args.case != 'conflict'):
        parser.error('conflict overrides apply only to conflict initialization')
    if args.reset and args.command != 'init':
        parser.error('--reset is valid only with init')
    path = STATE / (args.case + '.sqlite3')
    if args.command == 'init':
        STATE.mkdir(exist_ok=True)
        if path.exists():
            if not args.reset:
                parser.error('case exists; use --reset only when no process owns it')
            path.unlink()
        with sqlite3.connect(path) as db:
            db.executescript(SCHEMA)
            if args.case == 'conflict':
                payload = {'total': 42 if args.conflict_total is None else args.conflict_total}
                target = args.conflict_target or 'local-outbox-red'
                identity = make_identity('op-17', 'deliver', target, payload, 'rows-v2')
                put_effect(db, identity, payload, 'seed')
            if args.case == 'not_committed':
                identity = make_identity('op-17', 'deliver', 'local-outbox-blue', {'total': 13}, 'rows-v2')
                db.execute('INSERT INTO operations VALUES(?,?,?,?)',
                           (identity['key'], canonical(identity), 'terminal_not_committed', None))
        print(json.dumps({'initialized': args.case}))
        return
    if args.command == 'resolve':
        if args.case != 'unknown' or not path.is_file():
            parser.error('resolve requires initialized unknown state')
        payload = {'total': 13}
        identity = make_identity('op-17', 'deliver', 'local-outbox-blue', payload, 'rows-v2')
        with sqlite3.connect(path) as db:
            result = put_effect(db, identity, payload, 'later_resolution')
        print(json.dumps(result))
        return
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        print(json.dumps({table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]
                          for table in ('operations', 'calls', 'effects')}, indent=2))


if __name__ == '__main__':
    main()
