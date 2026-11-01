"""Full isolated author/repair/review/crash/resume journey. No real providers."""
import json
import subprocess
import sys
from unittest.mock import patch
from tests.helpers import HardeningTest, PACKAGE
from plovi import runner, state
from plovi.util import write_json


class FactoryJourneyTests(HardeningTest):
    def test_repair_crash_resume_review_complete_once(self):
        schema = self.root / 'fixture-schema.json'
        write_json(schema, {'ready': True})
        reader = f"import json\nfrom pathlib import Path\ndef ready(): return json.loads(Path({str(schema)!r}).read_text()).get('ready', False)\n"
        repaired = reader.replace(".get('ready', False)", ".get('health', {}).get('ready', False)")
        behavior = 'import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 2)\n'
        self.fixture([
            {'writes': {'test_app.py': behavior, 'test_fixture_helper.py': reader}},
            {'report': {'status': 'test_fixture_repair', 'reason': 'Fixture schema reader is stale',
                        'test_paths': [{'repository': 'app', 'path': 'test_fixture_helper.py'}], 'checks': ['fixture-health']}},
            {'writes': {'test_fixture_helper.py': repaired}},
            {'report': {'status': 'complete', 'repair_approved': True}},
            {'writes': {'app.py': 'VALUE = 2\n'}},
            {},
        ], stages=['implement-tests', 'implement', 'review'])
        self.plan['checks'].append({'id': 'fixture-health', 'repository': 'app', 'parser': 'generic',
                                   'command': {'argv': [sys.executable, '-c', "from test_fixture_helper import ready; assert ready(); print('fixture ready')"]},
                                   'success_pattern': 'fixture ready', 'phases': ['setup', 'green']})
        watchers = []
        output = self.root/'watch.jsonl'
        stream = output.open('w')
        self.addCleanup(stream.close)
        original_save = state.save
        def observe(root, value):
            original_save(root, value)
            if value.get('status') == 'running' and not watchers:
                watchers.append(subprocess.Popen([sys.executable, str(PACKAGE/'bin/plovi'), '--project',str(self.project.root),
                                                  'watch','sample','--json','--seconds','30'],env=self.env,
                                                 stdout=stream,stderr=subprocess.PIPE))
        original_accept = runner.accept_evidence
        def accept(project, manifest, stage, saved, evidence):
            original_accept(project, manifest, stage, saved, evidence)
            if stage == 'implement-tests': write_json(schema, {'health': {'ready': True}})
            if stage == 'implement': raise KeyboardInterrupt()
        with patch.object(state, 'save', side_effect=observe), patch.object(runner, 'accept_evidence', side_effect=accept):
            stopped = runner.run(self.project, self.plan)
        self.assertEqual(stopped['status'], 'cancelled')
        self.assertEqual(stopped['completed'], ['implement-tests', 'implement'])
        self.assertEqual(len(self.calls()), 5)
        watchers[0].communicate(timeout=10)
        self.assertEqual(watchers[0].returncode, 1)
        stream.flush()
        rows=[json.loads(line) for line in output.read_text().splitlines()]
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(all('baseline' not in row and 'attempts' not in row for row in rows))
        result=runner.run(self.project,self.plan,resume=True)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['completed'],self.plan['stages'])
        self.assertEqual(len(self.calls()),6)
        self.assertEqual(result['test_repairs'][0]['status'],'accepted')
        from plovi.state import read_events
        events,_=read_events(state.directory(self.project,'sample'))
        names=[x['event'] for x in events]
        self.assertIn('repair_started',names)
        self.assertIn('repair_accepted',names)
        self.assertIn('check_finished',names)
        self.assertEqual(len({x['sequence'] for x in events}),len(events))

    def test_malformed_report_and_stalled_tool_are_bounded(self):
        self.fixture([{'report': {'status': 'complete', 'assumptions': [42]}}])
        result=runner.run(self.project,self.plan)
        self.assertEqual(result['status'],'escalated')
        self.assertEqual(len(self.calls()),1)
        self.root=self.root/'second';self.root.mkdir()
        self.fixture([{'tool_stall':True}])
        self.plan['limits']['tool_timeout_seconds']=1
        result=runner.run(self.project,self.plan)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(len(self.calls()),1)
        self.assertEqual(result['attempts'][0]['classification'],'tool-stalled')
