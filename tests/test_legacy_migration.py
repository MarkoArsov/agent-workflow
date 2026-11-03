import json
from pathlib import Path
from unittest.mock import patch
from tests.helpers import HardeningTest
from plovi import runner, state
from plovi.util import WorkflowError, digest, json_text, write_json


class LegacyMigrationTests(HardeningTest):
    def stopped(self, *, baseline_case=False):
        self.fixture([
            {'writes': {'test_app.py': 'import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 2)\n'}},
            {'report': {'status': 'spec_conflict', 'reason': 'Reviewed fixture upgrade is needed'}},
        ], stages=['implement-tests', 'implement', 'review'])
        if baseline_case:
            checkout = Path(self.project.root)
            (checkout / 'test_baseline.py').write_text('import unittest\nclass Baseline(unittest.TestCase):\n def test_existing(self):self.assertEqual(1, 1)\n')
            self.git(checkout, 'add', 'test_baseline.py');self.git(checkout, 'commit', '-m', 'Initialize baseline regression')
        saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(saved['completed'], ['implement-tests'])
        root = state.directory(self.project, 'sample')
        old = json.loads((root / 'binding.json').read_text())
        old.pop('identity_selector', None)
        write_json(root / 'binding.json', old)
        saved['binding_sha256'] = digest(json_text(old))
        state.save(root, saved)
        self.plan['recovery'] = {'test_checkpoint': {
            'binding_sha256': saved['binding_sha256'],
            'escalation_sha256': digest(saved['escalation']['reason'])}}
        self.save_plan()
        return root

    def test_preview_preserves_saved_run_and_provider_count(self):
        root = self.stopped(); before = (root / 'state.json').read_bytes()
        result = self.task_cli('migrate', 'sample')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'migration_ready')
        self.assertEqual((root / 'state.json').read_bytes(), before)
        self.assertEqual(len(self.calls()), 2)

    def test_apply_rechecks_and_preserves_tests_without_new_inference(self):
        self.stopped()
        result = self.task_cli('migrate', 'sample', '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = state.read(self.project, 'sample')
        self.assertEqual(saved['completed'], ['implement-tests'])
        self.assertEqual(saved['status'], 'interrupted')
        self.assertNotIn('escalation', saved)
        self.assertEqual(len(self.calls()), 2)
        self.assertTrue(saved['stage_evidence']['implement-tests']['passed'])
        repeated = self.task_cli('migrate', 'sample', '--apply')
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertTrue(json.loads(repeated.stdout)['reused'])
        self.assertEqual(len(self.calls()), 2)
        from plovi import ledger
        migrated = [e for e in ledger.events(self.project, {'kind': 'task', 'id': 'sample'}) if e['type'] == 'checkpoint.migrated']
        self.assertEqual([(e['actor']['kind'], e['data']['binding_sha256']) for e in migrated],
                         [('person', saved['binding_sha256'])], 'one person-actor event, none for the repeated no-op')
        # Continuing implementation still sees the renewed frozen set.
        write_json(self.scenario, [{}, {}, {'writes': {'app.py': 'VALUE = 2\n'}}, {}])
        resumed = self.task_cli('resume', 'sample')
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(len(self.calls()), 4)

    def test_modified_frozen_test_is_refused_and_preserved(self):
        root = self.stopped(); before = (root / 'state.json').read_bytes()
        path = Path(self.project.root) / 'test_app.py'
        path.write_text(path.read_text().replace('VALUE, 2', 'VALUE, 9'))
        result = self.task_cli('migrate', 'sample', '--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('frozen', result.stderr.lower())
        self.assertEqual((root / 'state.json').read_bytes(), before)
        self.assertIn('VALUE, 9', path.read_text())
        self.assertEqual(len(self.calls()), 2)

    def test_changed_requirement_is_refused(self):
        self.stopped()
        (self.manifest_path.parent / 'requirements.md').write_text('Changed product expectation')
        result = self.task_cli('migrate', 'sample', '--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requirements', result.stderr.lower())
        self.assertEqual(len(self.calls()), 2)

    def test_foreign_product_edit_is_refused(self):
        self.stopped()
        (Path(self.project.root) / 'app.py').write_text('VALUE = 7\n')
        result = self.task_cli('migrate', 'sample', '--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('foreign', result.stderr.lower())
        self.assertEqual(len(self.calls()), 2)

    def test_failed_red_proof_keeps_escalation(self):
        self.stopped()
        with patch('plovi.verification.run_checks', return_value=[{'passed': False}]):
            from plovi.checkpoints import migrate
            with self.assertRaisesRegex(WorkflowError, 'red'):
                migrate(self.project, 'sample', apply=True)
        self.assertEqual(state.read(self.project, 'sample')['status'], 'escalated')
        self.assertEqual(len(self.calls()), 2)

    def reviewed_merge(self):
        root = self.stopped()
        checkout = Path(self.project.root)
        self.git(checkout, 'checkout', '-b', 'upstream')
        (checkout / 'README.md').write_text('Approved upstream repair\n')
        self.git(checkout, 'add', 'README.md'); self.git(checkout, 'commit', '-m', 'Upstream repair')
        upstream = self.git(checkout, 'rev-parse', 'HEAD')
        self.git(checkout, 'checkout', 'main')
        self.git(checkout, 'merge', '--no-ff', 'upstream', '-m', 'Integrate approved upstream')
        merged = self.git(checkout, 'rev-parse', 'HEAD')
        self.plan['recovery']['approved_commits'] = {'app': [upstream, merged]}
        return merged

    def test_explicit_merge_handoff_preserves_authored_tests(self):
        merged = self.reviewed_merge()
        self.plan['recovery']['approved_merges'] = {'app': [merged]};self.save_plan()
        result = self.task_cli('migrate', 'sample', '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = state.read(self.project, 'sample')
        self.assertEqual(saved['baseline']['app']['head'], merged)
        self.assertEqual(saved['completed'], ['implement-tests'])
        self.assertEqual(len(self.calls()), 2)

    def test_merge_needs_separate_explicit_approval(self):
        self.reviewed_merge();self.save_plan()
        result = self.task_cli('migrate', 'sample', '--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('repair commit', result.stderr)
        self.assertEqual(len(self.calls()), 2)

    def test_fixture_correction_uses_independent_routes_without_reauthoring(self):
        self.stopped();checkout = Path(self.project.root)
        helper = checkout / 'test_fixture_helper.py'
        helper.write_text('raise RuntimeError("fixture setup broken")\n')
        self.git(checkout, 'add', helper.name);self.git(checkout, 'commit', '-m', 'Add reviewed fixture-health helper')
        sha = self.git(checkout, 'rev-parse', 'HEAD')
        self.plan['recovery']['approved_commits'] = {'app':[sha]}
        self.plan['checks'].append({'id':'fixture-health','repository':'app','parser':'generic',
            'command':{'argv':[__import__('sys').executable,'-c','import test_fixture_helper; print("fixture ready")']},
            'success_pattern':'fixture ready','phases':['setup','green']})
        self.plan['recovery']['test_checkpoint']['fixture_request'] = {
            'status':'test_fixture_repair','reason':'Repair the reproduced helper setup defect',
            'test_paths':[{'repository':'app','path':helper.name}],'checks':['fixture-health']}
        self.save_plan()
        steps=json.loads(self.scenario.read_text())
        steps += [{'writes':{helper.name:'# fixture ready\n'}},{'report':{'status':'complete','repair_approved':True}}]
        write_json(self.scenario,steps)
        result=self.task_cli('migrate','sample','--apply')
        self.assertEqual(result.returncode,0,result.stderr)
        saved=state.read(self.project,'sample')
        self.assertEqual(saved['completed'],['implement-tests'])
        self.assertEqual(saved['test_repairs'][0]['status'],'accepted')
        self.assertEqual(len(self.calls()),4)
        self.assertEqual(len({c['pid'] for c in self.calls()}),4)
        self.assertTrue(all(c['passed'] for c in saved['stage_evidence']['implement-tests']['checks']))
        repeated=self.task_cli('migrate','sample','--apply')
        self.assertEqual(repeated.returncode,0,repeated.stderr)
        self.assertEqual(len(self.calls()),4)

    def test_exact_upstream_baseline_test_update_preserves_authored_slice(self):
        self.stopped(baseline_case=True);checkout=Path(self.project.root)
        path=checkout/'test_baseline.py';path.write_text('# reviewed upstream compatibility change\n'+path.read_text())
        self.git(checkout,'add',path.name);self.git(checkout,'commit','-m','Approved baseline compatibility')
        self.plan['recovery']['approved_commits']={'app':[self.git(checkout,'rev-parse','HEAD')]};self.save_plan()
        result=self.task_cli('migrate','sample','--apply')
        self.assertEqual(result.returncode,0,result.stderr)
        saved=state.read(self.project,'sample')
        self.assertEqual(saved['completed'],['implement-tests'])
        self.assertEqual(saved['checkpoint_migration']['source_test_updates'][0]['path'],path.name)
        self.assertEqual(len(self.calls()),2)
