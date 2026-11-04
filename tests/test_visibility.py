"""Visibility and budgets (#47): attempt records, per-stage status with the next command, and per-task budgets."""
import json
from tests.helpers import HardeningTest
from plovi import progress, runner, state

BROKEN, FIXED = {"app.py": "VALUE = 2\n"}, {"app.py": "VALUE = 1\n"}
GENUINE = "A person must decide which export format users get"


class VisibilityTests(HardeningTest):
    def test_attempt_records_kind_time_turns_tokens(self):
        self.fixture([{}])
        saved = runner.run(self.project, self.plan, unattended=False)
        entry = saved["attempts"][0]
        self.assertEqual((entry["kind"], entry["turns"], entry["tokens_in"], entry["tokens_out"], entry["cost_usd"]),
                         ("attempt", 1, 10, 5, None))
        self.assertIsInstance(entry["duration_s"], float)
        self.assertEqual(entry["prompt_bytes"], len(self.calls()[0]["prompt"].encode("utf-8")))

    def test_status_shows_per_stage_summary_and_next_command(self):
        self.fixture([{"writes": BROKEN}, {"writes": FIXED}, {"report": {"status": "blocked", "reason": GENUINE}}],
                     stages=["implement", "review"])
        self.assertEqual(runner.run(self.project, self.plan, unattended=False)["status"], "escalated")
        text = self.task_cli("status", "sample")
        lines = text.stdout.splitlines()
        implement = next(line for line in lines if line.startswith("implement "))
        self.assertIn("attempts 1 · fix rounds 1 · challenges 0", implement)
        self.assertIn("tokens 20/10", implement)
        self.assertIn("cost unknown", implement)
        self.assertIn(GENUINE, text.stdout)
        self.assertEqual(lines[-1], "Next: plovi retry sample --note DECISION")
        data = json.loads(self.task_cli("status", "sample", "--json").stdout)
        self.assertEqual([(row["stage"], row["attempts"], row["fix_rounds"]) for row in data["stages"]],
                         [("implement", 1, 1), ("review", 1, 0)])
        self.assertEqual(data["next"], "plovi retry sample --note DECISION")

    def test_watch_events_name_same_session_continuations(self):
        self.fixture([{"writes": BROKEN}, {"writes": FIXED}])
        runner.run(self.project, self.plan, unattended=False)
        events, _ = progress.read_events(state.directory(self.project, "sample"))
        texts = [progress.event_text(dict(e, task="sample")) for e in events if e.get("event") == "fix_round"]
        self.assertEqual(len(texts), 1)
        self.assertIn("Continuing the same session: 1 check failed (round 1 of 2)", texts[0])


class BudgetTests(HardeningTest):
    def test_task_budget_pauses_with_inbox_item_and_override_resumes(self):
        self.fixture([{"writes": BROKEN}, {"writes": FIXED}])
        self.policy("budgets.task_attempts", "1")
        self.save_plan()
        saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual((saved["status"], saved["pause_reason"], saved["budget"]["which"]), ("paused", "budget", "attempts"))
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(progress.next_command(saved), "plovi resume sample --budget-attempts 2")
        inbox = self.task_cli("inbox")
        self.assertIn("Budget reached: attempts (1 of 1).", inbox.stdout)
        resumed = self.task_cli("resume", "sample", "--budget-attempts", "3")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        final = state.read(self.project, "sample")
        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["budget_overrides"], {"attempts": 3})

    def test_minutes_budget_pauses_before_the_next_attempt(self):
        self.fixture([{"writes": BROKEN}, {"writes": FIXED}])
        self.policy("budgets.task_minutes", "1")
        self.save_plan()
        original = runner.time.time
        clock = {"offset": 0.0}
        def later():
            return original() + clock["offset"]
        def first_attempt_takes_two_minutes(*args, **kwargs):
            clock["offset"] = 120.0
            return real_execute(*args, **kwargs)
        real_execute = runner.execute_process
        from unittest.mock import patch
        with patch.object(runner.time, "time", side_effect=later), \
                patch.object(runner, "execute_process", side_effect=first_attempt_takes_two_minutes):
            saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual((saved["status"], saved["budget"]["which"]), ("paused", "minutes"))
