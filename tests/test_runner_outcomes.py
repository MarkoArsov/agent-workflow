import json
from tests.helpers import HardeningTest
from plovi import runner, state
from plovi.providers import Events
from plovi.util import WorkflowError


class RunnerOutcomeTests(HardeningTest):
    def stop(self, kind):
        reason = "A person must resolve the fixture constraint"
        self.fixture([{"session": "stop-session", "report": {"status": kind, "reason": reason}}, {}])
        self.plan["limits"]["attempts_per_route"] = 2
        self.plan["routes"] = {"default": [
            {"provider": "codex", "model": "primary"},
            {"provider": "codex", "model": "fallback"}]}
        result = runner.run(self.project, self.plan)
        self.assertEqual(len(self.calls()), 1, f"{kind} must not retry or use a fallback")
        self.assertEqual(result["status"], "escalated")
        escalation = result["escalation"]
        self.assertEqual((escalation["stage"], escalation["kind"], escalation["reason"]),
                         ("implement", kind, reason))
        self.assertEqual(escalation["session"], "stop-session")
        self.assertEqual(escalation["route"]["model"], "primary")
        self.assertIsInstance(escalation["at"], (float, int))
        self.assertEqual(len(result["attempts"]), 1)
        return result

    def test_blocked_stops_after_one_attempt(self):
        self.stop("blocked")

    def test_spec_conflict_stops_after_one_attempt(self):
        self.stop("spec_conflict")

    def test_impossible_stops_after_one_attempt(self):
        self.stop("impossible")

    def test_all_reports_validate_required_fields_and_assumptions(self):
        for kind in ("complete", "needs_input", "blocked", "spec_conflict", "impossible"):
            with self.subTest(kind=kind):
                report = {"status": kind, "summary": "done", "question": "Which value?",
                          "reason": "Fixture constraint", "assumptions": ["Fixture is offline"]}
                events = Events(); events.text = [json.dumps(report)]
                self.assertEqual(events.report(), report)
                if kind != "complete":
                    key = "question" if kind == "needs_input" else "reason"
                    for bad in (None, "", "   ", 7, ["reason"]):
                        events.text = [json.dumps(report | {key: bad})]
                        self.assertIsNone(events.report(), (kind, key, bad))
                for bad in ("assumption", [1], {}, None):
                    events.text = [json.dumps(report | {"assumptions": bad})]
                    self.assertIsNone(events.report(), bad)

    def test_malformed_report_cannot_complete_stage(self):
        self.fixture([{"report": {"status": "complete", "assumptions": [42]}}])
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("implement", result["completed"])

    def test_transient_error_retries_in_fresh_session(self):
        self.fixture([{"error": "temporary transport failure"}, {}])
        self.plan["limits"]["attempts_per_route"] = 2
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(self.calls()), 2)
        self.assertNotIn("resume", self.calls()[1]["argv"])

    def test_ordinary_resume_preserves_escalation(self):
        first = self.stop("blocked")
        response = self.task_cli("resume", "sample")
        self.assertNotEqual(response.returncode, 0)
        self.assertIn("retry", response.stdout + response.stderr)
        self.assertEqual(state.read(self.project, "sample")["escalation"], first["escalation"])
        self.assertEqual(len(self.calls()), 1)

    def test_retry_keeps_history_and_adds_note_to_fresh_session(self):
        first = self.stop("spec_conflict")
        self.save_plan()
        note = self.root / "note.txt"; note.write_text("Use the approved offline fixture.")
        response = self.task_cli("retry", "sample", "--note", note)
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        saved = state.read(self.project, "sample")
        self.assertEqual(saved["status"], "complete")
        self.assertFalse(saved.get("escalation"))
        self.assertIn(first["escalation"], saved["escalation_history"])
        self.assertEqual(len(saved["attempts"]), 2)
        self.assertNotIn("resume", self.calls()[1]["argv"])
        self.assertIn("NOTE FROM THE PERSON", self.calls()[1]["prompt"])
        self.assertIn(note.read_text(), self.calls()[1]["prompt"])

    def test_escalation_survives_scope_violation(self):
        self.fixture([{"writes": {"outside.txt": "retained"},
                       "report": {"status": "impossible", "reason": "Missing fixture capability"}}])
        with self.assertRaisesRegex(WorkflowError, "Scope violation"):
            runner.run(self.project, self.plan)
        self.assertEqual(state.read(self.project, "sample")["escalation"]["kind"], "impossible")

    def test_needs_input_resumes_exact_session(self):
        self.fixture([{"session": "question-session", "report": {"status": "needs_input", "question": "Keep one?"}}, {}])
        self.assertEqual(runner.run(self.project, self.plan)["status"], "needs_input")
        result = runner.run(self.project, self.plan, resume=True, answer="Yes")
        self.assertEqual(result["status"], "complete")
        self.assertIn("question-session", self.calls()[1]["argv"])
        self.assertEqual(self.calls()[1]["prompt"], "Yes")
