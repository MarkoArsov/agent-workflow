from tests.helpers import HardeningTest
from plovi import runner

class ContractRecoveryTests(HardeningTest):
    def scenario(self, *, repairable=True, weaken=False):
        old='import unittest\nfrom app import VALUE\nFACTS = {"uncertain": True}\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 2)\n'
        new=old.replace('True','False')
        if weaken:new=new.replace('self.assertEqual(VALUE, 2)','self.assertTrue(True)')
        self.fixture([{'writes':{'test_app.py':old}},
            {'report':{'status':'spec_conflict','reason':'Test inputs contradict approved stage facts'}},
            {'report':{'status':'complete','repairable':repairable,'reason':'Input mistake with unchanged expected behavior','test_paths':[{'repository':'app','path':'test_app.py'}]}},
            {'writes':{'test_app.py':new}},
            {'report':{'status':'complete','repair_approved':True}},
            {'writes':{'app.py':'VALUE = 2\n'}},{}],stages=['implement-tests','implement','review'])
        self.plan['corrections']={'contract_review_rounds':1}

    def test_independent_input_correction_continues_without_user_stop(self):
        self.scenario();saved=runner.run(self.project,self.plan, unattended=False)
        self.assertEqual(saved['status'],'complete')
        self.assertEqual(saved['contract_reviews'][0]['status'],'accepted')
        self.assertEqual(len(self.calls()),7)

    def test_genuine_decision_still_stops(self):
        self.scenario(repairable=False);saved=runner.run(self.project,self.plan, unattended=False)
        self.assertEqual(saved['status'],'escalated')
        self.assertEqual(len(self.calls()),3)

    def test_assertion_weakening_is_rejected_before_implementation(self):
        from plovi.util import WorkflowError
        self.scenario(weaken=True)
        with self.assertRaisesRegex(WorkflowError,'protected assertions'):runner.run(self.project,self.plan, unattended=False)
        self.assertEqual(len(self.calls()),4)

    def test_partial_product_work_keeps_green_failure_as_implementation_feedback(self):
        import json
        self.scenario()
        steps=json.loads(self.scenario.read_text());steps[1]['writes']={'app.py':'VALUE = 3\n'}
        self.scenario.write_text(json.dumps(steps))
        saved=runner.run(self.project,self.plan, unattended=False)
        self.assertEqual(saved['status'],'complete')
        self.assertTrue(any(not c['passed'] for c in saved['contract_reviews'][0]['checks']))
        self.assertEqual(len(self.calls()),7)
