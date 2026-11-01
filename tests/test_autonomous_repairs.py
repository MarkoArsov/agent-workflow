import json
from tests.helpers import HardeningTest
from plovi import runner

class AutonomousRepairTests(HardeningTest):
    def fixture_repair(self, *, weaken=False, approve=True):
        test='import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 1)\n'
        broken='raise RuntimeError("fixture setup broken")\n'+test
        fixed=test if not weaken else test.replace('self.assertEqual(VALUE, 1)','self.assertTrue(True)')
        root=self.fixture([
            {'report':{'status':'test_fixture_repair','reason':'Fixture startup fails','test_paths':[{'repository':'app','path':'test_app.py'}],'checks':['fixture-health']}},
            {'writes':{'test_app.py':fixed}},
            {'report':{'status':'complete','repair_approved':approve}},
            {},
        ])
        (root/'test_app.py').write_text(broken)
        self.git(root,'add','test_app.py');self.git(root,'commit','-m','Initialize broken fixture')
        check=dict(self.plan['checks'][0],id='fixture-health',phases=['setup','green'])
        self.plan['checks'].append(check)
        return root

    def test_fixture_failure_enters_repair_loop(self):
        self.fixture_repair()
        from plovi import manifest
        self.assertIn('setup', getattr(manifest, 'PHASES', {'red', 'green'}), 'Fixture setup phase is missing')
        result=runner.run(self.project,self.plan)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(len(self.calls()),4)
        self.assertEqual(len({c['pid'] for c in self.calls()}),4)
        self.assertNotIn('PRIVATE_IMPLEMENTATION_REASONING',self.calls()[2]['prompt'])
        self.assertEqual(result['test_repairs'][0]['status'],'accepted')

    def test_repair_cannot_weaken_assertions(self):
        self.fixture_repair(weaken=True)
        result=runner.run(self.project,self.plan)
        self.assertNotEqual(result['status'],'complete')
        self.assertNotIn('implement',result['completed'])
        self.assertLessEqual(len(self.calls()),3)

    def test_repair_budget_exhaustion_stops(self):
        self.fixture_repair()
        self.plan['corrections']={'fixture_rounds':0}
        result=runner.run(self.project,self.plan)
        self.assertEqual(result['status'],'escalated')
        self.assertEqual(len(self.calls()),1)

    def test_requirement_change_requires_decision(self):
        self.fixture([{'report':{'status':'spec_conflict','reason':'Choose expected behavior'}}])
        result=runner.run(self.project,self.plan)
        self.assertEqual(result['status'],'escalated')
        self.assertEqual(len(self.calls()),1)

    def test_rejected_correction_is_restored_and_reauthored_within_budget(self):
        self.fixture_repair()
        steps=json.loads(self.scenario.read_text())
        steps[2]['report']['repair_approved']=False
        steps[3:3]=[steps[1],{'report':{'status':'complete','repair_approved':True}}]
        self.scenario.write_text(json.dumps(steps))
        result=runner.run(self.project,self.plan)
        self.assertEqual(result['status'],'complete')
        self.assertEqual([r['status'] for r in result['test_repairs']],['rejected','accepted'])
        self.assertEqual(len(self.calls()),6)
        self.assertIn('feedback',self.calls()[3]['prompt'])

    def test_reviewer_rejection_exhausts_without_repeating_implementation(self):
        root=self.fixture_repair(approve=False)
        original=(root/'test_app.py').read_text()
        steps=json.loads(self.scenario.read_text());steps[3:]=[steps[1],steps[2]]
        self.scenario.write_text(json.dumps(steps))
        result=runner.run(self.project,self.plan)
        self.assertEqual(result['status'],'escalated')
        self.assertEqual(len(self.calls()),5)
        self.assertEqual((root/'test_app.py').read_text(),original)
        self.assertIn('budget exhausted',result['escalation']['reason'])

    def test_repair_provider_failure_uses_approved_fallback_once(self):
        self.fixture_repair()
        steps=json.loads(self.scenario.read_text());steps.insert(1,{'error':'model not available'})
        self.scenario.write_text(json.dumps(steps))
        self.plan['routes']={'default':[{'provider':'codex','model':'fixture-model'}],
                             'implement-tests':[{'provider':'codex','model':'unavailable'},
                                                {'provider':'codex','model':'fallback'}]}
        result=runner.run(self.project,self.plan)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(len(self.calls()),5)
        self.assertIn('fallback',self.calls()[2]['argv'])

    def test_explicit_repair_contract_requires_both_routes_before_inference(self):
        from plovi.util import WorkflowError
        self.fixture([{}])
        self.plan['corrections']={'fixture_rounds':2}
        self.plan['routes']={'implement':[{'provider':'codex','model':'fixture-model'}]}
        with self.assertRaisesRegex(WorkflowError,'test-author and review routes'):
            runner.run(self.project,self.plan)
        self.assertEqual(self.calls(),[])
