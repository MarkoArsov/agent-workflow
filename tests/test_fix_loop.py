"""Implement owns the fix loop (#47): failing final checks continue the same session first."""
from tests.helpers import HardeningTest
from plovi import runner

BROKEN, FIXED = {"app.py": "VALUE = 2\n"}, {"app.py": "VALUE = 1\n"}


class FixLoopTests(HardeningTest):
    def run_plan(self, steps, attempts=1, **corrections):
        self.fixture(steps)
        self.plan["corrections"] = corrections
        self.plan["limits"]["attempts_per_route"] = attempts
        return runner.run(self.project, self.plan, unattended=False)

    def kinds(self, saved):
        return [attempt.get("kind") for attempt in saved["attempts"]]

    def test_failing_final_checks_continue_same_session_then_pass(self):
        saved = self.run_plan([{"writes": BROKEN}, {"writes": FIXED}])
        self.assertEqual(saved["status"], "complete")
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["argv"][-2:], ["fixture-session-1", "-"])
        self.assertTrue(calls[1]["prompt"].startswith("The named checks failed."))
        self.assertIn("behavior: 1", calls[1]["prompt"])
        self.assertEqual(self.kinds(saved), ["attempt", "fix-round"])

    def test_fix_rounds_do_not_consume_route_attempts(self):
        saved = self.run_plan([{"writes": BROKEN}, {"writes": BROKEN}, {"writes": FIXED}], attempts=1)
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(self.kinds(saved), ["attempt", "fix-round", "fix-round"])

    def test_rounds_exhausted_fall_back_to_fresh_attempt(self):
        saved = self.run_plan([{"writes": BROKEN}, {"writes": BROKEN}, {"writes": FIXED}], attempts=2, same_session_rounds=1)
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(self.kinds(saved), ["attempt", "fix-round", "attempt"])
        fresh = self.calls()[2]
        self.assertNotIn("resume", fresh["argv"])
        self.assertIn("OBSERVED FAILED VERIFICATION", fresh["prompt"])

    def test_no_session_id_skips_rounds(self):
        saved = self.run_plan([{"writes": BROKEN, "no_session": True}, {"writes": FIXED}], attempts=2)
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(self.kinds(saved), ["attempt", "attempt"])
        self.assertNotIn("resume", self.calls()[1]["argv"])
