import json
from unittest.mock import patch
from tests.helpers import WorkspaceTest

class ProgressEventTests(WorkspaceTest):
    def api(self):
        from plovi import state
        self.assertTrue(hasattr(state, 'Reporter'), 'Live event reporting is missing')
        return state.Reporter

    def test_watch_emits_heartbeat_without_state_dump(self):
        reporter = self.api()(self.root / 'run', 'fixture-run')
        reporter.emit('stage_started', stage='implement')
        first = reporter.pulse(force=True)
        self.assertEqual(first['stage'], 'implement')
        self.assertNotIn('baseline', first)
        self.assertIn('heartbeat_at', first)

    def test_activity_is_distinct_from_worker_heartbeat(self):
        reporter = self.api()(self.root / 'run', 'fixture-run')
        with patch('time.time', return_value=10): reporter.activity('tool-start')
        with patch('time.time', return_value=30): live = reporter.pulse(force=True)
        self.assertEqual(live['activity_at'], 10)
        self.assertEqual(live['heartbeat_at'], 30)
        self.assertEqual(live['activity'], 'tool-start')
        self.assertTrue(live['tool_active'])
        with patch('time.time', return_value=31):reporter.activity('provider_output')
        self.assertTrue(reporter.pulse(force=True)['tool_active'])
        reporter.activity('tool-end')
        self.assertFalse(reporter.pulse(force=True)['tool_active'])

    def test_partial_event_and_rotation_are_safe(self):
        from plovi import state
        reporter = self.api()(self.root / 'run', 'fixture-run')
        reporter.emit('stage_started', stage='implement')
        rows, cursor = state.read_events(reporter.root, 0)
        self.assertEqual(len(rows), 1)
        with (reporter.root / 'events.jsonl').open('ab') as stream: stream.write(b'{partial')
        rows, again = state.read_events(reporter.root, cursor)
        self.assertEqual(rows, [])
        self.assertEqual(cursor, again)
        (reporter.root / 'events.jsonl').write_text('')
        rows, cursor = state.read_events(reporter.root, again)
        self.assertEqual(cursor['offset'], 0)

    def test_cancel_reports_owned_cleanup_failure(self):
        from plovi import process
        import sys
        def fail_stop(child):
            child.kill(); child.wait()
            raise PermissionError('fixture cleanup denied')
        with patch.object(process, 'stop', side_effect=fail_stop):
            result = process.execute([sys.executable, '-c', 'import time; time.sleep(10)'], self.root, cancel=lambda: True)
        self.assertEqual(result['reason'], 'cancellation_failure')

    def test_rotation_larger_than_previous_offset_keeps_new_events(self):
        from plovi import state
        reporter=self.api()(self.root/'run','run-a')
        reporter.emit('first')
        _,cursor=state.read_events(reporter.root)
        path=reporter.root/'events.jsonl'
        path.replace(reporter.root/'rotated.jsonl')
        path.write_text(json.dumps({'schema_version':1,'sequence':2,'event':'second','reason':'x'*500})+'\n')
        rows,cursor=state.read_events(reporter.root,cursor)
        self.assertEqual([r['event'] for r in rows],['second'])
        self.assertEqual(state.read_events(reporter.root,cursor)[0],[])

    def test_status_observer_uses_small_receipt_while_worker_owns_task(self):
        from plovi import state
        project=self.setup_project(self.repo('app'))
        root=state.directory(project,'sample')
        state.save(root,{'task':'sample','run_id':'live','status':'running','stage':'implement',
                         'baseline':{'large':'x'*100000}})
        self.assertLess((root/'status.json').stat().st_size,1000)
        (root/'state.json').unlink()
        with state.lock(root/'runner.lock'):
            self.assertEqual(state.observe(project,'sample')['status'],'running')
        self.assertNotIn('baseline',json.loads((root/'status.json').read_text()))


from tests.helpers import HardeningTest

class VerificationCleanupTests(HardeningTest):
    def test_check_cleanup_failure_stops_before_another_model_request(self):
        from plovi import runner,state
        from plovi.process import CleanupFailure
        self.fixture([{}]);self.plan['limits']['attempts_per_route']=2
        result={'exit_code':None,'reason':'cancellation_failure','child_pid':123,
                'output':'','duration_seconds':0}
        with patch('plovi.verification.execute',return_value=result):
            with self.assertRaises(CleanupFailure):runner.run(self.project,self.plan, unattended=False)
        saved=state.read(self.project,'sample')
        self.assertEqual(saved['status'],'escalated')
        self.assertEqual(saved['escalation']['kind'],'cancellation_failure')
        self.assertEqual(saved['cleanup']['child_pid'],123)
        self.assertEqual(len(self.calls()),1)
