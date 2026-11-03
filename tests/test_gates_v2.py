"""Gates reclassified (#47): advisory size below a ceiling, declared protected paths, plan rebinds and adoption on resume."""
from unittest.mock import patch
from tests.helpers import HardeningTest
from plovi import ledger, runner
from plovi.evidence import evidence_markdown

WORKFLOW = ".github/workflows/ci.yml"


class GateTests(HardeningTest):
    def run_plan(self, steps, **limits):
        self.fixture(steps)
        self.plan["limits"].update(limits)
        return runner.run(self.project, self.plan, unattended=False)

    def events(self, kind):
        return [e for e in ledger.events(self.project) if e["type"] == kind]

    def test_budget_overshoot_is_advisory_below_ceiling(self):
        saved = self.run_plan([{"writes": {"app.py": "VALUE = 1\n# changed\n", "other.py": "X = 1\n"}}], max_changed_files=1)
        self.assertEqual(saved["status"], "complete")
        self.assertEqual((saved["diff_advisory"]["files"], saved["diff_advisory"]["limit"]["files"]), (2, 1))
        body = evidence_markdown(saved, self.plan)
        self.assertIn(f"Size: 2 files, {saved['diff']['lines']:,} lines (limit 1/1,500)", body)
        self.assertEqual([e["data"]["files"] for e in self.events("limits.exceeded")], [2])

    def test_ceiling_requires_approval(self):
        writes = {f"module_{n}.py": "X = 1\n" for n in range(5)}
        saved = self.run_plan([{"writes": writes}], max_changed_files=1)
        self.assertEqual(saved["status"], "needs_approval")
        self.assertEqual(saved["pending_approvals"][0]["kind"], "size")

    def test_declared_protected_path_needs_no_extra_approval(self):
        self.fixture([{"writes": {WORKFLOW: "name: ci\n"}}])
        self.plan["repositories"][0]["paths"].append(WORKFLOW)
        self.plan["protected_paths"] = [".github/workflows/*.yml"]
        saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(saved.get("pending_approvals"), [])

    def test_undeclared_protected_path_still_stops(self):
        self.fixture([{"writes": {WORKFLOW: "name: ci\n"}}])
        self.plan["repositories"][0]["paths"].append(WORKFLOW)
        saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(saved["status"], "needs_approval")
        self.assertEqual(saved["pending_approvals"][0]["kind"], "protected_paths")

    def test_protected_paths_must_be_protected_by_policy(self):
        from plovi import manifest
        from plovi.util import WorkflowError
        self.fixture([{}])
        self.plan["protected_paths"] = ["docs/**"]
        self.save_plan()
        with self.assertRaisesRegex(WorkflowError, "protected_paths.*paths.protected"):
            manifest.load(self.manifest_path, self.project)


class PlanRevisionTests(HardeningTest):
    def revise_after_implement(self):
        """Edit a plan file after implement's checks pass, before review starts: a stage boundary."""
        original = runner.verify_stage
        plan_file = self.manifest_path.parent / "requirements.md"
        def verify(project, manifest, stage, *args, **kwargs):
            evidence = original(project, manifest, stage, *args, **kwargs)
            if stage == "implement" and "Revised." not in plan_file.read_text():
                plan_file.write_text(plan_file.read_text() + "\nRevised.\n")
            return evidence
        return patch.object(runner, "verify_stage", side_effect=verify)

    def test_plan_revision_rebinds_at_stage_boundary(self):
        self.fixture([{}, {}, {}], stages=["implement", "review"])
        with self.revise_after_implement():
            saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(len(saved["revisions"]), 1)
        self.assertEqual([c["prompt"].count("Revised.") > 0 for c in self.calls()], [False, True, True])
        rebound = [e for e in ledger.events(self.project) if e["type"] == "plan.rebound"]
        self.assertEqual([(e["actor"]["kind"], e["data"]["old"] != e["data"]["new"]) for e in rebound], [("plovi", True)])

    def test_plan_change_during_stage_stops(self):
        plan_file = self.root / "plans" / "implementation.md"
        self.fixture([{"writes": {str(plan_file): "Fixture behavior. Changed while implementing.\n"}}, {}], stages=["implement"])
        saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual((saved["status"], saved["pause_reason"]), ("paused", "plan_changed"))
        self.assertEqual(saved["error"], "The plan changed while implement was running; resume to continue with the new plan")
        self.assertNotIn("implement", saved["completed"])
        resumed = runner.run(self.project, self.plan, resume=True, unattended=False)
        self.assertEqual(resumed["status"], "complete")
        self.assertIn("Changed while implementing.", self.calls()[-1]["prompt"])

    def test_plan_revision_without_approval_stops_with_next_command(self):
        from plovi.manifest import plan_sha256
        self.fixture([{}, {}, {}], stages=["implement", "review"])
        self.save_plan()
        ledger.append(self.project, {"subject": {"kind": "task", "id": "sample"}, "type": "plan.approved",
                                     "actor": {"kind": "person", "name": "fixture"}, "reason": "Approved for the test",
                                     "data": {"plan_sha256": plan_sha256(self.plan), "auto": False}})
        with self.revise_after_implement():
            saved = runner.run(self.project, self.plan, unattended=False, require_plan_approval=True)
        self.assertEqual((saved["status"], saved["pause_reason"]), ("paused", "plan_changed"))
        self.assertEqual(saved["next_command"], "plovi approve sample --plan, then plovi resume sample")
        self.assertEqual(len(self.calls()), 1)


class AdoptionTests(HardeningTest):
    def stop_for_input(self):
        self.fixture([{"session": "asking", "report": {"status": "needs_input", "question": "Keep the parser?"}}, {}])
        self.assertEqual(runner.run(self.project, self.plan, unattended=False)["status"], "needs_input")
        return self.project.root

    def commit(self, root, path, text, *extra):
        (root / path).write_text(text)
        self.git(root, "add", path)
        self.git(root, "commit", "-m", f"Change {path}", *extra)
        return self.git(root, "rev-parse", "HEAD")

    def test_task_owned_commits_adopted_on_resume(self):
        root = self.stop_for_input()
        sha = self.commit(root, "app.py", "VALUE = 1\n# kept\n")
        saved = runner.run(self.project, self.plan, resume=True, answer="Yes", unattended=False)
        self.assertEqual(saved["status"], "complete")
        adopted = [e for e in ledger.events(self.project) if e["type"] == "commits.adopted"]
        self.assertEqual([(e["data"]["commits"], e["data"]["author"]) for e in adopted], [([sha], {"kind": "person"})])

    def test_foreign_author_commit_stops(self):
        from plovi.util import WorkflowError
        root = self.stop_for_input()
        sha = self.commit(root, "app.py", "VALUE = 1\n# foreign\n", "--author", "Other Person <other@example.invalid>")
        with self.assertRaisesRegex(WorkflowError, f"were not made by this task: {sha[:12]}.*recovery.approved_commits"):
            runner.run(self.project, self.plan, resume=True, answer="Yes", unattended=False)

    def test_merge_commit_stops(self):
        from plovi.util import WorkflowError
        root = self.stop_for_input()
        self.git(root, "switch", "-c", "side")
        self.commit(root, "side.py", "X = 1\n")
        self.git(root, "switch", "-")
        self.commit(root, "app.py", "VALUE = 1\n# main\n")
        self.git(root, "merge", "--no-ff", "-m", "Merge side", "side")
        with self.assertRaisesRegex(WorkflowError, "were not made by this task"):
            runner.run(self.project, self.plan, resume=True, answer="Yes", unattended=False)

    def test_interrupted_attempt_edits_adopted(self):
        self.fixture([{"writes": {"app.py": "VALUE = 1\nPARTIAL = True\n"}, "error": "temporary transport failure"}, {}])
        self.assertEqual(runner.run(self.project, self.plan, unattended=False)["status"], "failed")
        self.assertEqual(self.load_attempts()[0]["artifact_changes"]["app"].keys(), {"app.py"})
        saved = runner.run(self.project, self.plan, resume=True, unattended=False)
        self.assertEqual(saved["status"], "complete")
        self.assertIn("Its edits are still in the checkout; continue from them.", self.calls()[1]["prompt"])
        self.assertIn("PARTIAL = True", (self.project.root / "app.py").read_text())

    def load_attempts(self):
        from plovi import state
        return state.read(self.project, "sample")["attempts"]


class ReceiptTests(HardeningTest):
    def started(self, name="first"):
        root = self.repo("app")
        self.setup_project(root, {"repositories": [{"id": "app", "path": "."}]})
        self.git(root, "add", "."); self.git(root, "commit", "-m", "Configure fixture")
        result = self.cli("task", "start", name, cwd=root, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        from plovi.project import load
        project = load(root)
        ledger.append(project, {"subject": {"kind": "task", "id": name}, "type": "task.claimed", "actor": dict(ledger.RUNNER),
                                "reason": "The runner claimed the task", "data": {"run_id": "r" * 32}})
        return project

    def test_receipt_rederived_from_ledger(self):
        from plovi import tasks
        project = self.started()
        receipt = tasks.receipt_path(project, "first")
        saved = receipt.read_text(); receipt.unlink()
        path = tasks.owned_checkout(project, "first", "app", "feature/first")
        self.assertTrue(path.endswith("first/app"), path)
        self.assertEqual(json_rows(receipt.read_text()), json_rows(saved))
        events = [e for e in ledger.events(project) if e["type"] == "receipt.rederived"]
        self.assertEqual([e["data"]["repository"] for e in events], ["app"])

    def test_receipt_of_other_task_stops(self):
        from plovi import tasks
        from plovi.util import WorkflowError, write_json
        project = self.started()
        receipt = tasks.receipt_path(project, "first")
        stolen = tasks.receipt_path(project, "second")
        value = __import__("json").loads(receipt.read_text())
        write_json(stolen, dict(value, task="second"))
        receipt.unlink()
        with self.assertRaisesRegex(WorkflowError, "belongs to task second"):
            tasks.owned_checkout(project, "first", "app", "feature/first")


def json_rows(text):
    import json
    return [{k: v for k, v in row.items() if k in {"repository", "branch", "path", "strategy"}} for row in json.loads(text)["repositories"]]
