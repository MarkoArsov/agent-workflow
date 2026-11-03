"""Reports are optional (#47): terminal markers, one same-session nudge, and checks decide."""
from tests.helpers import HardeningTest
from plovi import runner

BROKEN = {"app.py": "VALUE = 2\n"}


class ReportTests(HardeningTest):
    def run_plan(self, steps, **corrections):
        self.fixture(steps)
        self.plan["corrections"] = corrections
        return runner.run(self.project, self.plan, unattended=False)

    def kinds(self, saved):
        return [attempt.get("kind") for attempt in saved["attempts"]]

    def test_terminal_marker_completes_stage(self):
        saved = self.run_plan([{"text": "Changed the parser.\nPLOVI_STAGE_OK: implement"}])
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(saved["attempts"][0]["report"]["status"], "complete")

    def test_input_required_marker_asks(self):
        text = "PLOVI_INPUT_REQUIRED\n1. Which colour should the button be? Options: red, blue. I recommend blue. [stop:behaviour]"
        saved = self.run_plan([{"text": text}])
        self.assertEqual(saved["status"], "needs_input")
        self.assertIn("Which colour should the button be?", saved["pending_input"]["question"])
        self.assertEqual(len(self.calls()), 1)

    def test_missing_report_nudged_once_then_checks_decide(self):
        saved = self.run_plan([{"no_report": True}, {"no_report": True}])
        self.assertEqual(saved["status"], "complete")
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["argv"][-2:], ["fixture-session-1", "-"])
        self.assertIn("End with exactly one terminal line: PLOVI_STAGE_OK: implement", calls[1]["prompt"])
        self.assertEqual(self.kinds(saved), ["attempt", "nudge"])
        self.assertNotIn("escalation", saved)

    def test_missing_report_with_failing_checks_is_a_failed_attempt(self):
        saved = self.run_plan([{"no_report": True, "writes": BROKEN}, {"no_report": True}], same_session_rounds=0)
        self.assertEqual(saved["status"], "failed")
        self.assertNotIn("escalation", saved)
        self.assertEqual(self.kinds(saved), ["attempt", "nudge"])
