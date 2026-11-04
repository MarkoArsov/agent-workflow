"""One command layer: registry, actor/reason recording, previews by digest and the plan gate.

Digest contract these tests rely on: high-risk previews return "digest"; plan previews
return "plan_sha256" and approve --plan applies with --approve <plan_sha256>; a diff
approval applies with --approve <pending approval fingerprint>.
"""
from __future__ import annotations
import json
import threading
import tomllib
from tests.helpers import HardeningTest, InProcessCli
from tests.fixtures.control_plane import AGENT, AGENT_FLAGS, RUNNER, ControlPlaneMixin, rows
from plovi import runner, state
from plovi.util import read_json

RISKS = {"status": "none", "inbox": "none", "events": "none", "stats": "none", "commands": "none", "policy.show": "none",
         "projects.list": "none", "answer": "low", "retry": "low", "pause": "low", "resume": "low",
         "cancel": "low", "projects.add": "low", "projects.remove": "low", "rebuild-state": "low",
         "approve": "high", "policy.set": "high"}
MUTATING_COMMANDS = [("answer",), ("approve",), ("retry",), ("pause",), ("resume",), ("cancel",),
                     ("policy", "set"), ("projects", "add"), ("projects", "remove"), ("rebuild-state",)]
SHA256 = r"^[0-9a-f]{64}$"


class OperationCliTests(InProcessCli, ControlPlaneMixin, HardeningTest):
    SUBPROCESS_TESTS = frozenset({"test_commands_json_lists_every_operation", "test_mutating_operations_record_actor_and_reason",
                                  "test_retry_with_note", "test_pause_stops_before_next_stage_and_resume_continues"})

    def asking(self, *questions):
        steps = [{"session": "asking-session", "report": {"status": "needs_input", "question": q}} for q in questions]
        self.fixture(steps + [{}], stages=["implement"])
        self.save_plan()
        result = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(result["status"], "needs_input")
        return result

    def saved(self):
        return state.read(self.project, "sample")

    def test_commands_json_lists_every_operation(self):
        self.fixture([{}], stages=["implement"])
        response = self.task_cli("commands", "--json")
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        operations = rows(json.loads(response.stdout), "operations")
        by_name = {row["name"]: row for row in operations}
        self.assertLessEqual(set(RISKS), set(by_name))
        for row in operations:
            self.assertLessEqual({"name", "summary", "arguments", "mutates", "risk"}, set(row))
        for name, risk in RISKS.items():
            with self.subTest(operation=name):
                row = by_name[name]
                self.assertEqual(row["risk"], risk)
                self.assertIs(row["mutates"], risk != "none")
                self.assertIsInstance(row["summary"], str)
                self.assertTrue(row["summary"].strip())
                self.assertIsInstance(row["arguments"], dict)
        listing = self.ok(self.task_cli("commands")).stdout
        for name in RISKS:
            self.assertIn(name, listing)

    def test_mutating_operations_record_actor_and_reason(self):
        for command in MUTATING_COMMANDS:
            with self.subTest(command=command):
                text = self.cli(*command, "--help", check=False).stdout
                for flag in ("--reason", "--actor-agent", "--via"):
                    self.assertIn(flag, text)
        self.asking("Keep the parser?")
        self.git(self.project.root, "config", "user.name", "Fixture Person")
        self.ok(self.task_cli("answer", "sample", "--text", "Yes", "--reason", "Answered for the person", *AGENT_FLAGS))
        answered = self.of_type("question.answered")
        self.assertEqual(len(answered), 1)
        self.assertEqual(answered[0]["actor"], AGENT)
        self.assertEqual(answered[0]["reason"], "Answered for the person")
        approvals = self.of_type("plan.approved")
        self.assertEqual([(e["actor"], e["data"]["auto"]) for e in approvals], [(AGENT, True)],
                         "the answer continuation self-approves the plan with the flag actor")
        self.ok(self.task_cli("cancel", "sample"))
        cancel = self.of_type("cancel.requested")[-1]
        self.assertEqual(cancel["actor"]["kind"], "person")
        self.assertEqual(cancel["actor"]["name"], "Fixture Person")
        self.assertIn("cancel", cancel["reason"].lower(), "the default reason names the command")

    def test_answer_with_text_and_file(self):
        self.asking("First question?", "Second question?")
        answer = self.root / "answer.txt"; answer.write_text("Second answer")
        self.assertEqual(self.task_cli("answer", "sample", "--text", "x", "--file", answer).returncode, 2)
        self.assertEqual(self.task_cli("answer", "sample").returncode, 2)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(self.saved()["status"], "needs_input")
        self.ok(self.task_cli("answer", "sample", "--text", "First answer"))
        self.assertEqual(self.saved()["status"], "needs_input")
        self.ok(self.task_cli("answer", "sample", "--file", answer))
        self.assertEqual(self.saved()["status"], "complete")
        self.assertEqual([call["prompt"] for call in self.calls()[1:]], ["First answer", "Second answer"])
        self.assertEqual([e["data"]["question"] for e in self.of_type("question.asked")],
                         ["First question?", "Second question?"])
        self.assertEqual(len(self.of_type("question.answered")), 2)

    def test_retry_with_note(self):
        self.fixture([{"session": "stop", "report": {"status": "blocked", "reason": "A person must choose the parser"}}, {}],
                     stages=["implement"])
        self.save_plan()
        self.assertEqual(runner.run(self.project, self.plan, unattended=False)["status"], "escalated")
        raised = self.of_type("escalation.raised")
        self.assertEqual(len(raised), 1)
        self.assertEqual((raised[0]["data"]["stage"], raised[0]["data"]["kind"]), ("implement", "blocked"))
        self.assertIn("A person must choose the parser", raised[0]["data"]["detail"])
        self.assertEqual(raised[0]["actor"], RUNNER)
        note = self.root / "note.txt"; note.write_text("Keep the recursive parser.")
        self.ok(self.task_cli("retry", "sample", "--note", note, "--reason", "Parser choice recorded"))
        self.assertEqual(self.saved()["status"], "complete")
        self.assertIn("Keep the recursive parser.", self.calls()[1]["prompt"])
        later = [e for e in self.task_events() if e["id"] > raised[0]["id"]]
        self.assertTrue([e for e in later if e["reason"] == "Parser choice recorded" and e["actor"]["kind"] == "person"],
                        "retry appends an event with the person and the reason")
        self.assertEqual([e["data"]["status"] for e in later if e["type"] == "run.finished"][-1:], ["complete"])

    def test_pause_stops_before_next_stage_and_resume_continues(self):
        self.fixture([{"sleep": 3}, {}], stages=["implement", "review"])
        self.save_plan()
        outcome = {}
        def work():
            try:
                outcome["result"] = runner.run(self.project, self.plan, unattended=False)
            except BaseException as exc:  # surfaced by the assertion below
                outcome["error"] = exc
        worker = threading.Thread(target=work)
        worker.start()
        self.wait_for(lambda: self.scenario.with_suffix(".calls.json").exists(), message="the first provider call")
        paused = self.task_cli("pause", "sample", "--reason", "Pause before review")
        worker.join(120)
        self.assertFalse(worker.is_alive())
        self.ok(paused)
        self.assertNotIn("error", outcome, outcome.get("error"))
        result = outcome["result"]
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["completed"], ["implement"])
        self.assertEqual(len(self.calls()), 1)
        summary = self.cli_json("status", "sample", "--json")
        self.assertEqual(summary["status"], "paused")
        self.assertIn("plovi resume sample", summary["next_action"])
        requested = self.of_type("pause.requested")
        self.assertEqual([e["reason"] for e in requested], ["Pause before review"])
        self.ok(self.task_cli("resume", "sample"))
        saved = self.saved()
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(saved["completed"], ["implement", "review"])
        self.assertEqual(len(self.calls()), 2, "resume runs only the remaining stage")
        self.assert_subsequence(self.task_types(), ["pause.requested", "run.paused", "run.resumed", "run.finished"])

    def test_cancel_records_event(self):
        self.asking("Keep the parser?")
        value = self.cli_json("cancel", "sample", "--reason", "Superseded by another task")
        self.assertIs(value["cancel_requested"], True)
        self.assertEqual(value["task"], "sample")
        self.assertTrue((state.directory(self.project, "sample") / "cancel.json").is_file())
        events = self.of_type("cancel.requested")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["reason"], "Superseded by another task")
        self.assertEqual(events[0]["actor"]["kind"], "person")

    def test_high_risk_without_digest_previews_and_changes_nothing(self):
        self.fixture([{}], stages=["implement"])
        self.save_plan()
        policy_file = self.project.root / "plovi.toml"
        before = policy_file.read_bytes()
        change = ("policy", "set", "limits.max_changed_files", "10", *AGENT_FLAGS, "--reason", "Keep diffs small")
        preview = self.cli_json(*change)
        self.assertIsInstance(preview["digest"], str)
        self.assertTrue(preview["digest"])
        self.assertEqual(policy_file.read_bytes(), before)
        self.assertEqual([e for e in self.ledger_events() if e["type"] == "policy.changed"], [])
        self.assertEqual(self.task_cli(*change, "--approve", "0" * 64).returncode, 2)
        self.assertEqual(policy_file.read_bytes(), before)
        self.ok(self.task_cli(*change, "--approve", preview["digest"]))
        self.assertEqual(tomllib.loads(policy_file.read_text())["limits"]["max_changed_files"], 10)
        changed = [e for e in self.ledger_events() if e["type"] == "policy.changed"]
        self.assertEqual([(e["actor"], e["reason"]) for e in changed], [(AGENT, "Keep diffs small")])
        plan = self.plan_preview()
        self.assertRegex(plan["plan_sha256"], SHA256)
        for name in self.plan["plan_files"]:
            self.assertIn(name, json.dumps(plan["plan_files"]))
        self.assertEqual(self.of_type("plan.approved"), [])

    def test_agent_actor_requires_digest_for_existing_approvals(self):
        self.fixture([{"writes": {f"change_{n}.py": "# change\n" for n in range(41)}}], stages=["implement"])
        self.policy("limits.ceiling_factor", "1")  # Stop at the limit (#47 default: 4x).
        self.save_plan()
        result = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(result["status"], "needs_approval")
        fingerprint = result["pending_approvals"][0]["fingerprint"]
        requested = self.of_type("approval.requested")
        self.assertEqual([(e["data"]["kind"], e["data"]["fingerprint"]) for e in requested], [("size", fingerprint)])
        self.task_cli("approve", "sample", "--size", *AGENT_FLAGS)
        self.assertEqual(self.task_cli("approve", "sample", "--size", *AGENT_FLAGS, "--approve", "0" * 64).returncode, 2)
        self.assertEqual(self.saved()["status"], "needs_approval")
        self.assertFalse(self.saved().get("approvals"))
        self.assertEqual(self.of_type("approval.granted"), [])
        policy_file = self.project.root / "plovi.toml"
        before = policy_file.read_bytes()
        refused = self.task_cli("policy", "set", "limits.max_changed_files", "10", "--yes", *AGENT_FLAGS)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(policy_file.read_bytes(), before)
        self.ok(self.task_cli("approve", "sample", "--size", *AGENT_FLAGS, "--reason", "Generated files", "--approve", fingerprint))
        self.assertEqual(self.saved()["status"], "complete")
        granted = self.of_type("approval.granted")
        self.assertEqual([(e["actor"], e["reason"], e["data"]["fingerprint"]) for e in granted],
                         [(AGENT, "Generated files", fingerprint)])

    def test_existing_json_output_shapes_preserved(self):
        self.fixture([{}], stages=["implement"])
        self.factory_ready()
        run = json.loads(self.ok(self.task_cli("run", self.manifest_path)).stdout)
        self.assertLessEqual({"task", "status", "completed", "attempts", "run_id", "checkouts", "manifest_path"}, set(run))
        self.assertEqual(run["status"], "complete")
        from plovi.progress import summary
        expected = summary(state.read(self.project, "sample"))
        machine = self.cli_json("status", "sample", "--json")
        self.assertLessEqual(set(expected), set(machine))
        for key in ("type", "schema_version", "task", "run_id", "status", "completed", "updated_at"):
            self.assertEqual(machine[key], expected[key])
        human = self.ok(self.task_cli("status", "sample")).stdout
        self.assertTrue(human.startswith("sample: complete"), human)
        with self.assertRaises(ValueError):
            json.loads(human)
        pipeline = self.cli_json("pipeline", "sample", "--no-watch", "--json")
        self.assertLessEqual({"task", "status", "reused", "tracking"}, set(pipeline))
        self.assertEqual(pipeline["status"], "complete")
        cancel = self.cli_json("cancel", "sample")
        self.assertLessEqual({"task", "status", "cancel_requested", "detail"}, set(cancel))


class PlanApprovalTests(InProcessCli, ControlPlaneMixin, HardeningTest):
    SUBPROCESS_TESTS = frozenset({"test_approval_of_different_hash_rejected"})

    def prepared(self):
        self.fixture([{}], stages=["implement"])
        self.factory_ready()

    def evidence(self):
        return read_json(state.directory(self.project, "sample") / "state.json", {})

    def test_unattended_worker_refuses_without_plan_approval(self):
        self.prepared()
        response = self.task_cli("run", self.manifest_path, "--unattended")
        self.assertEqual(response.returncode, 2, response.stdout + response.stderr)
        self.assertIn("plovi approve sample --plan", response.stderr)
        self.assertEqual(self.calls(), [], "no provider started")
        self.assertEqual(self.evidence().get("completed", []), [])
        self.assertEqual(self.of_type("plan.approved"), [])
        self.assertEqual(self.of_type("run.started"), [])

    def test_approval_of_different_hash_rejected(self):
        self.prepared()
        preview = self.plan_preview()
        approved = preview["plan_sha256"]
        self.assertRegex(approved, SHA256)
        self.assertEqual(self.plan_preview()["plan_sha256"], approved, "the plan hash is stable")
        apply = ("approve", "sample", "--plan", "--manifest", self.manifest_path, "--approve")
        self.assertEqual(self.task_cli(*apply, "0" * 64).returncode, 2)
        (self.manifest_path.parent / "requirements.md").write_text("Revised fixture behavior.")
        revised = self.plan_preview()["plan_sha256"]
        self.assertNotEqual(revised, approved)
        self.assertEqual(self.task_cli(*apply, approved).returncode, 2)
        self.assertEqual(self.of_type("plan.approved"), [])
        self.ok(self.task_cli(*apply, revised))
        events = self.of_type("plan.approved")
        self.assertEqual([(e["data"]["plan_sha256"], e["data"]["auto"], e["actor"]["kind"]) for e in events],
                         [(revised, False, "person")])
        self.ok(self.task_cli("run", self.manifest_path, "--unattended"))
        self.assertEqual(self.evidence()["status"], "complete")
        self.assertEqual(len(self.of_type("plan.approved")), 1, "the worker relies on the recorded approval")

    def test_explicit_run_records_approval_automatically(self):
        self.prepared()
        expected = self.plan_preview()["plan_sha256"]
        self.git(self.project.root, "config", "user.name", "Fixture Person")
        self.ok(self.task_cli("run", self.manifest_path))
        self.assertEqual(self.evidence()["status"], "complete")
        events = self.of_type("plan.approved")
        self.assertEqual([(e["data"]["plan_sha256"], e["data"]["auto"]) for e in events], [(expected, True)])
        self.assertEqual(events[0]["actor"], {"kind": "person", "name": "Fixture Person"})
        self.assert_subsequence(self.task_types(), ["plan.approved", "run.started", "run.finished"])

    def test_pipeline_launch_records_approval_before_worker(self):
        self.prepared()
        expected = self.plan_preview()["plan_sha256"]
        self.ok(self.task_cli("pipeline", self.manifest_path, "--no-watch", "--json"))
        watched = self.ok(self.task_cli("watch", "sample", "--json"))
        self.assertEqual(json.loads(watched.stdout.splitlines()[-1])["status"], "complete")
        events = self.of_type("plan.approved")
        self.assertEqual([(e["data"]["plan_sha256"], e["data"]["auto"]) for e in events], [(expected, True)])
        self.assert_subsequence(self.task_types(), ["plan.approved", "run.started", "run.finished"])
        self.assertEqual([e["actor"] for e in self.of_type("run.started")], [RUNNER])

    def test_policy_can_disable_worker_gate(self):
        self.prepared()
        self.ok(self.task_cli("policy", "set", "execution.require_plan_approval", "false", "--yes"))
        shown = self.cli_json("policy", "show")
        self.assertIs(shown["values"]["execution"]["require_plan_approval"], False)
        self.ok(self.task_cli("run", self.manifest_path, "--unattended"))
        self.assertEqual(self.evidence()["status"], "complete")
        self.assertEqual(self.of_type("plan.approved"), [])
