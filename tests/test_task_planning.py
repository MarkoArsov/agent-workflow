import copy
from pathlib import Path
from tests.helpers import WorkspaceTest
from plovi import detect, git_ops, profile
from plovi.setup import apply, propose
from plovi.util import WorkflowError


class TaskPlanningTests(WorkspaceTest):
    def test_new_project_defaults_to_worktree(self):
        root = self.repo("app")
        proposal = propose(root, {"confirmed_defaults": True})
        self.assertEqual(proposal["profile"]["repositories"][0]["checkout_strategy"], "worktree")
        self.assertFalse((root / ".plovi").exists())

    def test_multiple_repositories_and_findings_agree_on_worktree(self):
        first = self.repo("workspace/app"); self.repo("workspace/checks")
        result = detect.scan(first.parent)
        for repo in result["profile"]["repositories"]:
            with self.subTest(repository=repo["id"]):
                self.assertEqual(repo["checkout_strategy"], "worktree")
                finding = next(f for f in result["findings"]
                               if f["repository"] == repo["id"] and f["subject"] == "checkout_strategy")
                self.assertEqual(finding["value"], "worktree")

    def test_explicit_checkout_and_commit_opt_out_survive_setup(self):
        for strategy in ("current-checkout", "feature-branch"):
            with self.subTest(strategy=strategy):
                root = self.repo(strategy)
                proposal = propose(root, {"confirmed_defaults": True, "profile": {
                    "repositories": [{"id": strategy, "checkout_strategy": strategy}],
                    "planning": {"commit_plans": False}}})
                apply(proposal, proposal["approval"])
                again = propose(root)
                self.assertEqual(again["profile"]["repositories"][0]["checkout_strategy"], strategy)
                self.assertIs(again["profile"]["planning"]["commit_plans"], False)

    def test_plan_commit_default_type_validation_and_approval_digest(self):
        root = self.repo("app")
        proposal = propose(root, {"confirmed_defaults": True})
        self.assertIs(proposal["profile"]["planning"]["commit_plans"], True)
        disabled = propose(root, {"confirmed_defaults": True, "profile": {"planning": {"commit_plans": False}}})
        self.assertNotEqual(proposal["approval"], disabled["approval"])
        for bad in ("false", 0, 1, None):
            value = copy.deepcopy(proposal["profile"])
            value["planning"]["commit_plans"] = bad
            with self.subTest(value=bad), self.assertRaisesRegex(WorkflowError, "commit_plans"):
                profile.validate(value, root)

    def test_prepare_before_manifest_creates_and_reuses_two_task_worktrees(self):
        root = self.repo("app")
        project = self.setup_project(root)
        self.git(root, "add", "."); self.git(root, "commit", "-m", "Configure fixture")
        original = self.git(root, "rev-parse", "HEAD")
        checkouts = []
        for task in ("first", "second"):
            branch = project.profile["git"]["branch_template"].format(task=task)
            plan = {"task": task, "repositories": [{"id": "app", "access": "write", "branch": branch,
                                                      "paths": ["ai-plans/**"]}]}
            paths = git_ops.prepare(project, plan)
            checkout = Path(paths["app"])
            self.assertNotEqual(checkout, root)
            self.assertEqual(self.git(checkout, "branch", "--show-current"), branch)
            self.assertFalse((checkout / "ai-plans" / task / "pipeline.json").exists())
            self.assertEqual(git_ops.prepare(project, plan), paths)
            checkouts.append(checkout)
        self.assertNotEqual(*checkouts)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), original)
        self.assertEqual(self.git(root, "branch", "--show-current"), "main")
        self.assertEqual(self.git(root, "status", "--porcelain"), "")
