"""Existing-project reuse regression; standard library, local subprocesses only.

Defaults to ../agent-forge beside the repository tests directory. Set
AGENT_FORGE_ROOT to test a separate skill copy. FORGE_REUSE_CORRUPT_OUTPUT=1
is an intentional failure control: it corrupts the fresh report before checking.
These fixture tools are synthetic task tools, not an Agent Forge execution engine.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(os.environ.get('AGENT_FORGE_ROOT', Path(__file__).resolve().parents[1] / 'agent-forge')).resolve()
HELPER = ROOT / 'scripts/forge.py'

RENDERER = '''import json, pathlib, sys
source, template, output = map(pathlib.Path, sys.argv[1:])
rows = json.loads(source.read_text())
assert isinstance(rows, dict) and rows and all(isinstance(k, str) and type(v) is int for k, v in rows.items()), 'invalid source'
text = template.read_text()
assert text.count('{{rows}}') == text.count('{{total}}') == 1, 'invalid template'
assert not output.exists(), 'refuse existing output'
output.write_text(text.replace('{{rows}}', '\\n'.join(f'{k}: {v}' for k, v in rows.items())).replace('{{total}}', str(sum(rows.values()))))
'''
CHECKER = '''import json, pathlib, re, sys
source, template, output = map(pathlib.Path, sys.argv[1:])
rows = json.loads(source.read_text())
text = output.read_text()
headings = re.findall(r'^# .+$', text, re.M)
summary = text.split('# Summary\\n', 1)[1].split('\\n\\n# Total\\n', 1)[0].splitlines()
total_match = re.search(r'^# Total\\n(-?\\d+)$', text, re.M)
total = int(total_match.group(1)) if total_match else None
footer = template.read_text().split('{{total}}', 1)[1]
checks = [headings == ['# Summary', '# Total'], summary == [f'{k}: {v}' for k, v in rows.items()], total == sum(rows.values()), text.endswith(footer)]
print(json.dumps({'ok': all(checks), 'headings': headings, 'rows': summary, 'total': total, 'footer_preserved': checks[3]}))
sys.exit(0 if all(checks) else 1)
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExistingProjectReuse(unittest.TestCase):
    def test_existing_project_repair_revalidation_and_fresh_run(self):
        self.assertTrue(HELPER.is_file(), 'Set AGENT_FORGE_ROOT to the skill copy being tested')
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            project = base / 'report-agent'
            commands = []

            def execute(arguments, expected=0):
                run = subprocess.run([sys.executable, *map(str, arguments)], cwd=project if project.exists() else base,
                                     capture_output=True, text=True)
                commands.append({'arguments': list(map(str, arguments)), 'returncode': run.returncode,
                                 'stdout': run.stdout, 'stderr': run.stderr})
                self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
                return run

            def cli(*arguments, expected=0):
                return json.loads(execute([HELPER, *arguments], expected).stdout)

            cli('init', project, '--project-id', 'report-agent')
            index = json.loads((project / 'toolbox/index.json').read_text())
            searches = []

            def search(location):
                # Exercise the actual index search before each authored durable asset.
                found = cli('find', project, '--query', location)['matches']
                for match in found:
                    if '://' not in match['location']:
                        self.assertTrue((project / match['location']).is_file())
                searches.append({'query': location, 'matches': [r['id'] for r in found],
                                 'decision': 'Adapt matching task resource or create distinct run evidence; preserve history'})

            def write(location, value):
                search(location)
                path = project / location
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2))

            def add(location, kind='evidence', status='draft', evidence=None):
                if any(r['location'] == location for r in index['resources']):
                    return
                index['resources'].append({
                    'id': re.sub('[^a-z0-9]+', '-', location.lower()).strip('-'),
                    'purpose': 'Synthetic reuse fixture ' + location, 'kind': kind, 'location': location,
                    'version': digest(project / location), 'input_contract': 'Local named integer rows or recorded task evidence',
                    'output_contract': 'Source-derived report or traceable artifact; no external effects',
                    'dependencies': [], 'status': status, 'used_by': ['step-01', 'check-01'],
                    'validation': {'method': 'Actual local tool execution or direct inventory inspection', 'evidence': evidence or []},
                    'replaces': None, 'reuse_decision': 'Searched index; distinct resource preserves prior task history'})

            def save_index():
                write('toolbox/index.json', index)

            write('PLAYBOOK.md', '# Synthetic report playbook\nVersion: 1.0.0\n'
                  'Manual only; one active writer; no external actions.\n'
                  'step-01: Inspect existing resources, search before each asset, freeze source checks.\n'
                  'step-02: Render to an unused output; preserve the existing template and history.\n'
                  'step-03: Independently check exact headings, rows, total and custom footer.\n'
                  '| check-01 | Exact current source report | Existing independent checker | runs/current/check.json |\n'
                  'Stop within three attempts and ten minutes, or earlier on uncertain effects/check failure.\n')
            write('template.md', '# Summary\n{{rows}}\n\n# Total\n{{total}}\n\nOwner annotation: keep exact wording.\n')
            write('scripts/render.py', RENDERER)
            write('scripts/check.py', CHECKER)
            write('inputs/rows.json', {'Earlier': 6})
            # Private content is synthetic and intentionally excluded from the public index.
            (project / '.private').mkdir()
            (project / '.private/interview.md').write_text('Synthetic private interview, never reusable task content.')
            for location, kind in [('template.md', 'template'), ('scripts/render.py', 'script'),
                                   ('scripts/check.py', 'script'), ('inputs/rows.json', 'input')]:
                add(location, kind)
            save_index()
            self.assertEqual(len(cli('find', project, '--query', 'template.md')['matches']), 1)

            def render(source, output):
                search(output)
                return execute(['scripts/render.py', source, 'template.md', output])

            def check(source, output, expected=0):
                return json.loads(execute(['scripts/check.py', source, 'template.md', output], expected).stdout)

            (project / 'outputs').mkdir()
            render('inputs/rows.json', 'outputs/report-01.md')
            prior = check('inputs/rows.json', 'outputs/report-01.md')
            self.assertTrue(prior['ok'])
            write('runs/prior/check.json', prior)
            add('outputs/report-01.md', 'output', 'validated', ['runs/prior/check.json'])
            add('runs/prior/check.json')
            save_index()
            # Existing-project mutations: source changes, another historical output is
            # left unindexed, and an old validation claim loses its evidence.
            render('inputs/rows.json', 'outputs/report-02.md')
            renderer = next(r for r in index['resources'] if r['location'] == 'scripts/render.py')
            renderer.update(status='validated', validation={'method': 'Old validation claim',
                                                            'evidence': ['runs/lost-render-evidence.json']})
            save_index()
            protected = {name: digest(project / name) for name in
                         ('template.md', 'scripts/render.py', 'scripts/check.py',
                          'outputs/report-01.md', 'outputs/report-02.md', 'runs/prior/check.json', '.private/interview.md')}
            old_source = digest(project / 'inputs/rows.json')
            changed = {'Zero': 0, 'East': 12, 'West': 19}
            write('inputs/rows.json', changed)
            before = cli('audit', project, expected=1)
            self.assertTrue(any('runs/lost-render-evidence.json' in e for e in before['errors']))

            # Concrete honest repair happens in the task fixture, not inside forge.py.
            renderer.update(status='draft', validation={'method': 'Old evidence missing; fresh validation pending', 'evidence': []})
            save_index()
            inventory_failure = cli('audit', project, expected=1)
            self.assertTrue(any('unindexed durable file: outputs/report-02.md' in e for e in inventory_failure['errors']))
            add('outputs/report-02.md', 'output')
            historical = next(r for r in index['resources'] if r['location'] == 'outputs/report-02.md')
            historical['input_contract'] = 'Historical source provenance not independently established; not current-source validation'
            save_index()
            self.assertEqual(renderer['status'], 'draft')
            self.assertFalse((project / 'runs/lost-render-evidence.json').exists())
            criteria = {'checks': [{'id': 'check-01', 'expected': changed,
                                    'method': 'Execute independent checker and compare exact current source rows, total and footer'}]}
            # The oracle is frozen outside candidate project write ownership.
            oracle = base / 'reviewer-criteria.json'
            oracle.write_text(json.dumps(criteria))
            oracle_hash = digest(oracle)
            write('runs/current/acceptance.json', criteria)
            snapshot_hash = digest(project / 'runs/current/acceptance.json')
            write('runs/current/provenance.json', {'old_source_sha256': old_source,
                  'current_source_sha256': digest(project / 'inputs/rows.json'), 'current_rows': changed,
                  'initial_audit': before, 'inventory_audit': inventory_failure, 'repair': 'Draft missing-evidence claim; index historical output without inventing provenance'})
            render('inputs/rows.json', 'outputs/report-03.md')
            if os.environ.get('FORGE_REUSE_CORRUPT_OUTPUT') == '1':
                fresh = project / 'outputs/report-03.md'
                fresh.write_text(fresh.read_text().replace('# Total\n31', '# Total\n30'))
            current = check('inputs/rows.json', 'outputs/report-03.md')
            self.assertTrue(current['ok'])
            self.assertEqual(current['rows'], ['Zero: 0', 'East: 12', 'West: 19'])
            self.assertEqual(current['total'], 31)
            self.assertTrue(current['footer_preserved'])
            write('runs/current/check.json', current)
            renderer.update(status='validated', validation={'method': 'Fresh existing-renderer execution plus independent checker',
                            'evidence': ['runs/current/check.json'], 'bindings': [
                                {'role': 'source', 'location': 'inputs/rows.json', 'sha256': digest(project / 'inputs/rows.json')},
                                {'role': 'evidence', 'location': 'runs/current/check.json', 'sha256': digest(project / 'runs/current/check.json')}]})
            self.assertNotEqual(old_source, digest(project / 'inputs/rows.json'))
            playbook = project / 'PLAYBOOK.md'
            write('PLAYBOOK.md', playbook.read_text().replace('Version: 1.0.0', 'Version: 1.1.0') +
                  '\nSaved lesson: inventory historical outputs; draft unsupported validation claims before fresh revalidation. '
                  'Never fabricate missing evidence. Freeze checks before rendering; compare row identities because totals may coincide.\n')
            self.assertIn('Never fabricate missing evidence.', playbook.read_text())
            # Run affected checks and zero regression AFTER saving operating learning.
            self.assertTrue(check('inputs/rows.json', 'outputs/report-03.md')['ok'])
            write('inputs/zero.json', {'Zero': 0, 'Five': 5})
            render('inputs/zero.json', 'outputs/zero-regression.md')
            zero = check('inputs/zero.json', 'outputs/zero-regression.md')
            self.assertEqual(zero['total'], 5)
            self.assertEqual(zero['rows'], ['Zero: 0', 'Five: 5'])
            write('runs/current/zero-check.json', zero)
            # Useful negative control: structural audit is not domain acceptance.
            write('outputs/corrupt-control.md', (project / 'outputs/report-03.md').read_text().replace('# Total\n31', '# Total\n30'))
            rejected = check('inputs/rows.json', 'outputs/corrupt-control.md', expected=1)
            self.assertFalse(rejected['ok'])
            self.assertEqual(rejected['total'], 30)
            write('runs/current/negative-check.json', rejected)
            review = json.loads((ROOT / 'templates/run-review.json').read_text())
            review.update(project_id='report-agent', run_id='current', run_key='synthetic:' + digest(project / 'inputs/rows.json'), status='passed')
            review['versions']['acceptance_snapshot'] = {'location': 'runs/current/acceptance.json', 'sha256': snapshot_hash}
            review['checks'] = [dict(criteria['checks'][0], status='pass', evidence=['runs/current/check.json'], observed=changed)]
            review['repairs'] = [{'failure': before['errors'], 'correction': 'Historical output indexed draft; missing evidence claim replaced by fresh inspected evidence',
                                  'saved_learning': 'PLAYBOOK.md version 1.1.0', 'regression': zero}]
            review['terminal_reason'] = 'Frozen source outcome passed; final audit and preservation asserted by integration test'
            write('runs/current/review.json', review)
            self.assertTrue(cli('audit-run', project, '--record', 'runs/current/review.json', '--criteria', oracle,
                                '--criteria-sha256', oracle_hash)['ok'])
            config = json.loads((project / 'agent.json').read_text())
            config.update(status='ready')
            config['execution']['mode'] = 'manual'
            config['authority'].update(source='Synthetic local integration fixture', allowed=['local fixture only'])
            config['bounds'].update(max_attempts=3, max_minutes=10, max_depth=0, max_concurrency=0, max_workers=0, max_cost_usd=0)
            config['capabilities']['observed'] = [name + ': actual fixture artifact/search/check execution' for name in config['capabilities']['required']]
            write('agent.json', config)
            write('runs/current/searches.json', searches)
            write('runs/current/commands.json', commands)
            for file in sorted(project.rglob('*')):
                if file.is_file() and '.private' not in file.parts:
                    add(file.relative_to(project).as_posix(), 'output' if file.parent.name == 'outputs' else 'evidence')
            for entry in index['resources']:
                if entry['id'] in ('instructions', 'playbook', 'config', 'toolbox-index'):
                    entry.update(status='validated', validation={'method': 'Actual current source fixture and inventory review', 'evidence': ['runs/current/check.json']})
            save_index()
            self.assertTrue(cli('audit', project, '--ready')['ok'])
            self.assertEqual({r['location'] for r in index['resources']},
                             {f.relative_to(project).as_posix() for f in project.rglob('*') if f.is_file() and '.private' not in f.parts})
            self.assertEqual(len([r for r in index['resources'] if r['location'] == 'template.md']), 1)
            self.assertEqual(historical['status'], 'draft')
            self.assertFalse((project / 'runs/lost-render-evidence.json').exists())
            self.assertEqual(digest(oracle), oracle_hash)
            self.assertEqual(digest(project / 'runs/current/acceptance.json'), snapshot_hash)
            for name, original_hash in protected.items():
                self.assertEqual(digest(project / name), original_hash, name)


if __name__ == '__main__':
    unittest.main()
