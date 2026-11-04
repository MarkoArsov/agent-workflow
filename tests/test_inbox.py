"""The inbox is derived from the ledger: each item kind appears and its action resolves it.

Text layout fixed by test_text_format_snapshot (requirements leave it open):
    "N item(s) need(s) you." then a blank line, then per item, separated by blank lines:
    "<local YYYY-MM-DD HH:MM; tests run the CLI with TZ=UTC0>  <kind>  <task>[  <title when it differs from task>]"
    "  <reason>"
    "  Next: <action labels joined by '; '>"
An empty inbox prints "Nothing needs you."
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from tests.helpers import HardeningTest, InProcessCli
from tests.fixtures.control_plane import RUNNER, ControlPlaneMixin, rows
from plovi import runner, state
from plovi.util import read_json, user_data, write_json

ITEM_KEYS = {"id", "kind", "project", "subject", "title", "reason", "created_at", "actions"}


def local(created_at):
    return datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def render(items):
    if not items:
        return "Nothing needs you.\n"
    header = "1 item needs you." if len(items) == 1 else f"{len(items)} items need you."
    blocks = []
    for item in items:
        task = item["subject"]["id"]
        head = f"{local(item['created_at'])}  {item['kind']}  {task}"
        if item["title"] != task:
            head += f"  {item['title']}"
        blocks.append("\n".join([head, "  " + item["reason"], "  Next: " + "; ".join(a["label"] for a in item["actions"])]))
    return header + "\n\n" + "\n\n".join(blocks) + "\n"


class InboxTests(InProcessCli, ControlPlaneMixin, HardeningTest):
    # The snapshot needs the child's TZ=UTC0; this process keeps its own time zone.
    SUBPROCESS_TESTS = frozenset({"test_text_format_snapshot", "test_question_item_appears_and_clears_after_answer"})

    def single_item(self, kind, opening_type, operation, task="sample"):
        items = self.task_inbox(task)
        self.assertEqual([item["kind"] for item in items], [kind], items)
        item = items[0]
        self.assertEqual(set(item), ITEM_KEYS)
        self.assertEqual(item["project"], self.project.profile["project"]["id"])
        self.assertEqual(item["subject"], {"kind": "task", "id": task})
        self.assertEqual(item["title"], task)
        self.assertTrue(item["reason"].strip())
        opening = self.of_type(opening_type, task)[-1]
        self.assertEqual((item["id"], item["created_at"]), (opening["id"], opening["at"]))
        registered = {row["name"] for row in rows(self.cli_json("commands", "--json"), "operations")}
        for action in item["actions"]:
            self.assertLessEqual({"label", "operation", "args"}, set(action))
            self.assertIn(action["operation"], registered)
            self.assertIsInstance(action["args"], dict)
        matching = [a for a in item["actions"] if a["operation"] == operation]
        self.assertTrue(matching, f"{kind} offers {operation}")
        self.assertIn(task, json.dumps(matching[0]["args"]))
        return item, matching[0]

    def run_until(self, status, steps):
        self.fixture(steps, stages=["implement"])
        self.policy("limits.ceiling_factor", "1")  # Approval items appear at the limit (#47 default: 4x).
        self.save_plan()
        result = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(result["status"], status)
        return result

    def test_question_item_appears_and_clears_after_answer(self):
        self.run_until("needs_input", [{"session": "asking", "report": {"status": "needs_input",
                                                                        "question": "Keep the existing behavior?"}}, {}])
        response = self.task_cli("inbox")
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        item, _ = self.single_item("question", "question.asked", "answer")
        self.assertIn("Keep the existing behavior?", item["reason"])
        self.ok(self.task_cli("answer", "sample", "--text", "Yes, keep it."))
        self.assertEqual(state.read(self.project, "sample")["status"], "complete")
        self.assertEqual(self.task_inbox(), [])

    def test_plan_item_clears_after_approval(self):
        self.fixture([{}], stages=["implement"])
        self.save_plan()
        for _ in range(2):
            self.ok(self.task_cli("validate-plan", self.manifest_path))
        proposed = self.of_type("plan.proposed")
        self.assertEqual(len(proposed), 1, "one plan.proposed per task and plan hash")
        digest = proposed[0]["data"]["plan_sha256"]
        _, action = self.single_item("plan", "plan.proposed", "approve")
        self.assertIn(digest, json.dumps(action["args"]), "one command resolves the plan item")
        self.ok(self.task_cli("approve", "sample", "--plan", "--manifest", self.manifest_path, "--approve", digest))
        self.assertEqual(self.task_inbox(), [])

    def test_approval_item_clears_after_approve(self):
        result = self.run_until("needs_approval", [{"writes": {f"change_{n}.py": "# change\n" for n in range(41)}}])
        _, action = self.single_item("approval", "approval.requested", "approve")
        self.assertIn(result["pending_approvals"][0]["fingerprint"], json.dumps(action["args"]))
        self.ok(self.task_cli("approve", "sample", "--size", "--actor", "Fixture"))
        self.assertEqual(state.read(self.project, "sample")["status"], "complete")
        self.assertEqual(self.task_inbox(), [])

    def test_escalation_item_clears_after_retry(self):
        self.run_until("escalated", [{"session": "stop", "report": {"status": "blocked",
                                                                    "reason": "A person must choose the parser"}}, {}])
        item, _ = self.single_item("escalation", "escalation.raised", "retry")
        self.assertIn("A person must choose the parser", item["reason"])
        self.ok(self.task_cli("retry", "sample"))
        self.assertEqual(state.read(self.project, "sample")["status"], "complete")
        self.assertEqual(self.task_inbox(), [])

    def test_failed_item_clears_after_resume(self):
        self.run_until("failed", [{"error": "temporary fixture failure"}, {}])
        self.single_item("failed", "run.finished", "resume")
        self.assertEqual(self.of_type("run.finished")[-1]["data"]["status"], "failed")
        self.ok(self.task_cli("resume", "sample"))
        self.assertEqual(state.read(self.project, "sample")["status"], "complete")
        self.assertEqual(self.task_inbox(), [])

    def test_interrupted_item_clears_after_resume(self):
        saved = self.run_until("complete", [{}])
        saved.update(status="running", completed=[], active_stage="implement", stage_before=saved["baseline"],
                     stage_evidence={})
        state.save(state.directory(self.project, "sample"), saved)
        self.assertEqual(self.cli_json("status", "sample", "--json")["status"], "interrupted")
        self.assertEqual(self.cli_json("status", "sample", "--json")["status"], "interrupted")
        self.assertEqual(len(self.of_type("run.interrupted")), 1, "at most one interruption event per run")
        self.single_item("interrupted", "run.interrupted", "resume")
        self.ok(self.task_cli("resume", "sample"))
        self.assertEqual(state.read(self.project, "sample")["status"], "complete")
        self.assertEqual(self.task_inbox(), [])

    def ask(self, task, question):
        from plovi import ledger
        ledger.append(self.project, {"subject": {"kind": "task", "id": task}, "type": "question.asked",
                                     "actor": dict(RUNNER), "reason": "The provider asked a question",
                                     "data": {"run_id": task + "-run", "stage": "implement", "question": question}})

    def test_items_oldest_first_with_issue_titles(self):
        self.fixture([{"session": "asking", "report": {"status": "needs_input", "question": "Keep the parser?"}}, {}],
                     stages=["implement"])
        self.save_plan()
        self.ok(self.task_cli("task", "start", "alpha", "--issue", "example/repo#12", "--title", "Fix the parser"))
        created = self.of_type("task.created", "alpha")
        self.assertEqual([(e["data"]["issue"], e["data"]["title"]) for e in created], [("example/repo#12", "Fix the parser")])
        self.assertEqual(runner.run(self.project, self.plan, unattended=False)["status"], "needs_input")
        self.ask("alpha", "Which parser should stay?")
        registry = user_data() / "projects.json"
        entries = read_json(registry, [])
        write_json(registry, entries + [{"id": "gone", "root": str(self.root / "gone"), "added_at": "2026-11-02T00:00:00.000Z"}])
        response = self.task_cli("inbox")
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        self.assertIn("gone", response.stdout + response.stderr, "an unreachable registered root is reported")
        items = [item for item in rows(json.loads(response.stdout), "items") if item["subject"]["id"] in {"sample", "alpha"}]
        self.assertEqual([(i["subject"]["id"], i["kind"], i["title"]) for i in items],
                         [("sample", "question", "sample"), ("alpha", "question", "Fix the parser")])
        self.assertLessEqual(items[0]["created_at"], items[1]["created_at"])

    def test_text_format_snapshot(self):
        self.fixture([{}], stages=["implement"])
        empty = self.ok(self.task_cli("inbox", "--format", "text")).stdout
        self.assertEqual(empty, render([]))
        self.ok(self.task_cli("task", "start", "alpha", "--issue", "example/repo#12", "--title", "Fix the parser"))
        self.ask("alpha", "Keep the current parser?")
        one = self.inbox()
        self.assertEqual(self.ok(self.task_cli("inbox", "--format", "text")).stdout, render(one))
        self.ask("beta", "Which fixture stays?")
        both = self.inbox()
        self.assertEqual([i["subject"]["id"] for i in both], ["alpha", "beta"])
        self.assertEqual(self.ok(self.task_cli("inbox", "--format", "text")).stdout, render(both))
