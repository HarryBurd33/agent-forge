"""Deterministic integration fixture; no LLM, scheduler or external service."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'agent-forge/scripts/forge.py'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReportWorkflow(unittest.TestCase):
    def test_report_repair_learning_regression_and_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary).resolve() / 'report-agent'
            def cli(*arguments, expected=0):
                run = subprocess.run([sys.executable, str(HELPER), *map(str, arguments)], capture_output=True, text=True)
                self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
                return json.loads(run.stdout)

            cli('init', project, '--project-id', 'report-agent')
            config = json.loads((project / 'agent.json').read_text())
            index = json.loads((project / 'toolbox/index.json').read_text())
            for directory in ('inputs', 'outputs', 'runs'):
                (project / directory).mkdir()
            template = project / 'template.md'
            template.write_text('# Summary\n{rows}\n\n# Total\n{total}\n')
            template_hash = digest(template)
            rows = {'Alpha': 20, 'Beta': 22}
            source = project / 'inputs/rows.json'
            source.write_text(json.dumps(rows))
            playbook = project / 'PLAYBOOK.md'
            playbook.write_text(
                '# Report playbook\nVersion: 1.0.0\n'
                'Goal: local report using the existing template. Manual only; no external effects.\n'
                'Inputs: named integer rows; zero is valid. Output: Summary/Total headings and exact row sum.\n'
                'step-01: Search the index and inspect the template before creating any resource.\n'
                'step-02: Render each source row once; keep source and output separate.\n'
                'step-03: Check against source facts; repair within three attempts; save validated lessons and rerun.\n'
                '| check-01 | Total equals source sum; exact headings and rows | Independent source/output comparison | runs/review.json |\n'
                'Stop on unknown authority/effects or failed checks after three attempts. One writer only.\n'
            )
            criteria = project / 'runs/criteria.json'
            criteria.write_text(json.dumps({'check-01': 'Exact headings Summary/Total; every source row once; total equals source sum'}))
            criteria_hash = digest(criteria)
            before_playbook_hash = digest(playbook)

            def resource(ident, location, kind):
                return {'id': ident, 'purpose': 'Report integration fixture ' + ident,
                        'kind': kind, 'location': location, 'version': '1.0.0',
                        'input_contract': 'Named integer rows or local procedure/evidence',
                        'output_contract': 'Exact source report or traceable local artifact',
                        'dependencies': [], 'status': 'draft', 'used_by': ['step-01', 'check-01'],
                        'validation': {'method': 'Actual source/output comparison', 'evidence': []},
                        'replaces': None, 'reuse_decision': 'Inspected existing index; fixture addition required'}

            index['resources'].append(resource('report-template', 'template.md', 'template'))
            (project / 'toolbox/index.json').write_text(json.dumps(index))
            found = cli('find', project, '--query', 'report-template')['matches']
            self.assertEqual([x['id'] for x in found], ['report-template'])
            self.assertEqual((project / found[0]['location']).read_text(), template.read_text())

            def render(values, output):
                text = template.read_text().format(rows='\n'.join(name + ': ' + str(value) for name, value in values.items()), total=sum(values.values()))
                output.write_text(text)

            def check(input_path, output):
                values = json.loads(input_path.read_text())
                text = output.read_text()
                headings = re.findall(r'^# (.+)$', text, re.M)
                actual = int(text.rsplit('# Total\n', 1)[1].strip())
                valid_rows = all(len(re.findall('^' + re.escape(name + ': ' + str(value)) + '$', text, re.M)) == 1 for name, value in values.items())
                return {'expected': sum(values.values()), 'observed': actual,
                        'ok': actual == sum(values.values()) and headings == ['Summary', 'Total'] and valid_rows}

            report = project / 'outputs/report-01.md'
            render(rows, report)
            report.write_text(report.read_text().replace('# Total\n42', '# Total\n41'))
            initial = check(source, report)
            self.assertFalse(initial['ok'])
            self.assertEqual(initial['observed'], 41)
            render(rows, report)
            saved = playbook.read_text().replace('Version: 1.0.0', 'Version: 1.1.0')
            saved += '\nValidated lesson: derive each total from current source rows and independently check it before delivery; preserve evidence of stale incorrect outputs.\n'
            playbook.write_text(saved)
            self.assertEqual(playbook.read_text(), saved)
            self.assertNotEqual(digest(playbook), before_playbook_hash)
            self.assertEqual(digest(criteria), criteria_hash)
            repaired = check(source, report)
            self.assertTrue(repaired['ok'])
            self.assertEqual(repaired['observed'], 42)

            # A repeated request searches and reuses the same template, preserving zero.
            found_again = cli('find', project, '--query', 'report-template')['matches']
            self.assertEqual(len(found_again), 1)
            regression_source = project / 'inputs/rows-02.json'
            regression_source.write_text(json.dumps({'Zero': 0, 'Five': 5}))
            repeated = project / 'outputs/report-02.md'
            render(json.loads(regression_source.read_text()), repeated)
            regression = check(regression_source, repeated)
            self.assertTrue(regression['ok'])
            self.assertEqual(regression['observed'], 5)
            self.assertEqual(digest(template), template_hash)
            self.assertEqual(digest(criteria), criteria_hash)

            review = json.loads((ROOT / 'agent-forge/templates/run-review.json').read_text())
            review.update(project_id='report-agent', run_id='fixture-01', run_key='fixture:source-v1:manual-01', status='passed')
            review['checks'] = [{'id': 'check-01', 'expected': 42, 'method': 'Parse report and independently sum source rows', 'status': 'pass', 'evidence': ['runs/criteria.json'], 'observed': repaired['observed']}]
            review['attempts'] = [{'number': 1, 'result': initial}, {'number': 2, 'result': repaired}]
            review['repairs'] = [{'failure': initial, 'cause': 'Existing output total incorrect; upstream cause unknown', 'correction': 'Regenerate current source total and save operating lesson', 'playbook_version': '1.1.0', 'regression': regression}]
            review['versions']['acceptance_snapshot'] = {'location': 'runs/criteria.json', 'sha256': criteria_hash}
            review_path = project / 'runs/review.json'
            review_path.write_text(json.dumps(review))
            config['status'] = 'ready'
            config['execution']['mode'] = 'manual'
            config['authority'].update(source='Local test fixture', allowed=['local fixture files only'])
            config['capabilities']['observed'] = [x + ': local fixture execution' for x in config['capabilities']['required']]
            (project / 'agent.json').write_text(json.dumps(config))

            known = {x['location'] for x in index['resources']}
            for file in sorted(project.rglob('*')):
                if not file.is_file():
                    continue
                relative = file.relative_to(project).as_posix()
                if relative not in known:
                    ident = 'fixture-' + re.sub('[^a-z0-9]+', '-', relative.lower()).strip('-')
                    index['resources'].append(resource(ident, relative, 'output' if relative.startswith('outputs/') else 'evidence'))
            for entry in index['resources']:
                entry['version'] = '1.1.0' if entry['location'] == 'PLAYBOOK.md' else '1.0.0'
                entry['status'] = 'validated'
                entry['validation']['evidence'] = ['runs/review.json']
            (project / 'toolbox/index.json').write_text(json.dumps(index))
            self.assertTrue(cli('audit', project, '--ready')['ok'])
            self.assertEqual(len([x for x in index['resources'] if x['id'] == 'report-template']), 1)
            self.assertEqual({x['location'] for x in index['resources']}, {x.relative_to(project).as_posix() for x in project.rglob('*') if x.is_file()})


if __name__ == '__main__':
    unittest.main()
