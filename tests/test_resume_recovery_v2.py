import json
from pathlib import Path
from tests.helpers import WorkspaceTest, PACKAGE
from plovi.util import WorkflowError

class ResumeRecoveryTests(WorkspaceTest):
    def api(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('plovi.runtime_pin'), 'Pinned runtime routing is missing')
        from plovi import runtime_pin
        return runtime_pin

    def test_runtime_mismatch_is_explicit(self):
        pin=self.api(); receipt=pin.freeze(PACKAGE,self.root/'runtimes')
        (Path(receipt['path'])/'runtime/plovi/cli.py').write_text('tampered')
        with self.assertRaisesRegex(WorkflowError,'runtime'):pin.verify(receipt)

    def test_source_changes_do_not_mutate_pinned_runtime(self):
        # Portable immutable payload: changing source does not change the pinned copy.
        pin=self.api(); source=self.root/'source'; (source/'bin').mkdir(parents=True)
        (source/'bin/plovi').write_text('first')
        receipt=pin.freeze(source,self.root/'runtimes')
        (source/'bin/plovi').write_text('second')
        pin.verify(receipt)
        self.assertEqual((Path(receipt['path'])/'bin/plovi').read_text(),'first')

    def test_missing_runtime_stops_with_repair_action(self):
        pin=self.api()
        with self.assertRaises(WorkflowError):pin.verify({'path':str(self.root/'missing'),'digest':'0'*64})

    def test_wrong_account_stops_before_model(self):
        from plovi.providers import claude_environment
        from types import SimpleNamespace
        from unittest.mock import patch
        project=SimpleNamespace(config=self.root/'project')
        local=project.config/'local';local.mkdir(parents=True)
        config=self.root/'personal';config.mkdir()
        (local/'claude-account.json').write_text(json.dumps({'config_dir':str(config),'email':'personal@example.invalid'}))
        with patch('plovi.providers.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps({'loggedIn':True,'authMethod':'claude.ai','apiProvider':'firstParty','email':'other@example.invalid'}))):
            with self.assertRaises(WorkflowError):claude_environment(project,self.root)


from tests.helpers import HardeningTest

class LaunchRecoveryTests(HardeningTest):
    def test_repeated_pipeline_start_reuses_worker_and_observer_is_read_only(self):
        from plovi import state
        self.fixture([{'sleep':3}])
        self.plan['repositories'][0]['branch']='feature/sample'
        self.save_plan()
        first=self.task_cli('pipeline',self.manifest_path,'--no-watch','--json',check=True)
        result=json.loads(first.stdout)
        self.assertIn(result['status'],['starting','running'])
        second=self.task_cli('pipeline','sample','--no-watch','--json',check=True)
        self.assertTrue(json.loads(second.stdout)['reused'])
        observed=self.task_cli('watch','sample','--seconds','1','--json',check=True)
        self.assertIn(json.loads(observed.stdout.splitlines()[-1])['status'],['running','complete'])
        final=self.task_cli('watch','sample','--json',check=True)
        self.assertEqual(json.loads(final.stdout.splitlines()[-1])['status'],'complete')
        self.assertEqual(len(self.calls()),1)
        self.assertNotIn('baseline',final.stdout)
        receipt=json.loads((state.directory(self.project,'sample')/'runtime.json').read_text())
        self.assertNotEqual(Path(receipt['path']),PACKAGE)
        complete=self.task_cli('pipeline','sample','--no-watch','--json',check=True)
        self.assertTrue(json.loads(complete.stdout)['reused'])
        self.assertEqual(len(self.calls()),1)

    def test_changed_identity_selector_stops_before_another_request(self):
        from plovi import runner
        root=self.fixture([{'writes':{'.plovi/local/provider-identities.json':json.dumps({'codex':{'config_env':{'CODEX_HOME':str(self.root/'changed')}}})}}])
        local=self.project.config/'local';local.mkdir(exist_ok=True)
        (local/'provider-identities.json').write_text(json.dumps({'codex':{'config_env':{'CODEX_HOME':str(self.home/'codex')}}}))
        with self.assertRaisesRegex(WorkflowError,'identity configuration changed'):
            runner.run(self.project,self.plan, unattended=False)
        self.assertEqual(len(self.calls()),1)

    def test_required_unavailable_identity_stops_before_inference(self):
        from plovi import runner
        self.fixture([{}])
        local=self.project.config/'local';local.mkdir(exist_ok=True)
        (local/'provider-identities.json').write_text(json.dumps({'codex':{'verification':'required'}}))
        with self.assertRaisesRegex(WorkflowError,'cannot expose a verified account'):
            runner.run(self.project,self.plan, unattended=False)
        self.assertEqual(self.calls(),[])

    def test_status_reports_new_launch_instead_of_stale_terminal_state(self):
        from plovi import state
        from plovi.util import write_json
        self.fixture([{}])
        root=state.directory(self.project,'sample')
        write_json(root/'state.json',{'task':'sample','run_id':'old','status':'failed','error':'old failure'})
        write_json(root/'launch.json',{'run_id':'new','at':100})
        with state.lock(root/'launch.lock'):
            value=state.read(self.project,'sample')
            self.assertEqual(value['status'],'starting')
            self.assertEqual(value['run_id'],'new')
            self.assertNotIn('error',value)

    def test_pipeline_preserves_explicit_cancellation(self):
        from plovi import runner
        from plovi.entrypoint import launch
        from plovi.runtime_pin import freeze
        from plovi import state
        from plovi.util import write_json
        self.fixture([{'sleep':1}])
        runner.run(self.project,self.plan, unattended=False)
        root=state.directory(self.project,'sample')
        value=json.loads((root/'state.json').read_text());value['status']='cancelled'
        write_json(root/'state.json',value)
        write_json(root/'runtime.json',freeze(PACKAGE,self.root/'runtimes'))
        result=launch(self.project,'sample')
        self.assertEqual(result['status'],'cancelled')
        self.assertTrue(result['reused'])
        self.assertEqual(len(self.calls()),1)

    def test_runtime_upgrade_refuses_active_task_without_changing_receipt(self):
        from plovi import runtime_pin,state
        from plovi.util import write_json
        self.fixture([{}])
        root=state.directory(self.project,'sample')
        receipt=runtime_pin.freeze(PACKAGE,self.root/'runtimes')
        write_json(root/'runtime.json',receipt)
        original=(root/'runtime.json').read_bytes()
        with state.lock(root/'runner.lock'):
            with self.assertRaisesRegex(WorkflowError,'worker owns'):
                runtime_pin.dispatch(self.project,'sample',[],source=PACKAGE,upgrade=True)
        self.assertEqual((root/'runtime.json').read_bytes(),original)

    def test_foreign_edit_to_saved_output_stops_before_another_request(self):
        from plovi import runner,state
        root=self.fixture([{'writes':{'owned.py':'VALUE = 1\n'}}])
        value=runner.run(self.project,self.plan, unattended=False)
        value.update(completed=[],status='failed',active_stage='implement',stage_before=value['baseline'],stage_evidence={})
        state.save(state.directory(self.project,'sample'),value)
        (root/'owned.py').write_text('VALUE = 999\n')
        with self.assertRaisesRegex(WorkflowError,'artifacts changed'):
            runner.run(self.project,self.plan,resume=True, unattended=False)
        self.assertEqual(len(self.calls()),1)
        self.assertEqual((root/'owned.py').read_text(),'VALUE = 999\n')

    def test_running_direct_resume_returns_current_run_tracker_identity(self):
        from plovi import state,runtime_pin
        from plovi.entrypoint import launch
        from plovi.util import write_json
        self.fixture([{}])
        root=state.directory(self.project,'sample')
        write_json(root/'runtime.json',runtime_pin.freeze(PACKAGE,self.root/'runtimes'))
        write_json(root/'state.json',{'task':'sample','run_id':'current','status':'running'})
        write_json(root/'launch.json',{'run_id':'previous','claimed_at':1})
        with state.lock(root/'runner.lock'):
            self.assertEqual(launch(self.project,'sample')['tracking']['run_id'],'current')

    def test_watch_returns_action_exit_for_question_without_changing_run_exit_contract(self):
        self.fixture([{'report':{'status':'needs_input','question':'Proceed?'}}])
        self.plan['repositories'][0]['branch']='feature/sample'
        self.save_plan()
        started=self.task_cli('run',self.manifest_path,check=True)
        self.assertEqual(json.loads(started.stdout)['status'],'needs_input')
        observed=self.task_cli('watch','sample','--json')
        self.assertEqual(observed.returncode,1)
        self.assertEqual(json.loads(observed.stdout.splitlines()[-1])['status'],'needs_input')
        self.assertEqual(len(self.calls()),1)

    def test_observer_does_not_replace_resumed_status_with_old_launch(self):
        from plovi import state
        from plovi.util import write_json
        self.fixture([{}]);root=state.directory(self.project,'sample')
        state.save(root,{'task':'sample','run_id':'current-resume','status':'running','stage':'review'})
        write_json(root/'launch.json',{'run_id':'old-launch','at':1,'claimed_at':2})
        with state.lock(root/'runner.lock'):
            self.assertEqual(state.observe(self.project,'sample')['run_id'],'current-resume')
            self.assertEqual(state.read(self.project,'sample')['stage'],'review')
