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
