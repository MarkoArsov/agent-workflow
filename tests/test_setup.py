import json
from pathlib import Path
from tests.helpers import WorkspaceTest
from agent_workflow.setup import apply, merge, propose
from agent_workflow.project import resolve
from agent_workflow.util import WorkflowError

class SetupTests(WorkspaceTest):
    def test_read_only_preview_approval_and_idempotence(self):
        repo = self.repo("single")
        (repo / "tests").mkdir()
        (repo / "pyproject.toml").write_text('[project]\nname="fixture"\nversion="0.0.0"\n')
        before = {p.relative_to(repo) for p in repo.rglob("*")}
        p = propose(repo, {"confirmed_defaults": True})
        self.assertEqual(before, {p.relative_to(repo) for p in repo.rglob("*")})
        with self.assertRaises(WorkflowError):
            apply(p, "wrong")
        apply(p, p["approval"])
        first = {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
        again = propose(repo)
        self.assertFalse(again["changes"])
        apply(again, again["approval"])
        self.assertEqual(first, {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()})
        profile = json.loads((repo / ".agent-workflow/project.json").read_text())
        self.assertEqual(profile["repositories"][0]["commands"]["test"]["parser"], "unittest")

    def test_manual_configuration_and_prose_survive_multiple_reruns(self):
        repo = self.repo("custom")
        self.setup_project(repo)
        p = repo / ".agent-workflow/project.json"
        data = json.loads(p.read_text())
        data["tracking"]["provider"] = "linear"
        data["my_extension"] = {"enabled": True}
        del data["repositories"][0]["languages"]
        p.write_text(json.dumps(data))
        guide = repo / "PROJECT_WORKFLOW.md"
        guide.write_text(guide.read_text().replace("Tracker: none", "Tracker: edited") + "\nMy own instructions.\n")
        for _ in range(3):
            proposal = propose(repo)
            apply(proposal, proposal["approval"])
        self.assertEqual(json.loads(p.read_text()), data)
        self.assertIn("Tracker: edited", guide.read_text())
        self.assertIn("My own instructions.", guide.read_text())

    def test_stale_preview_cannot_overwrite_a_new_edit(self):
        repo = self.repo("stale")
        p = propose(repo, {"confirmed_defaults": True})
        (repo / "AGENTS.md").write_text("New instructions\n")
        with self.assertRaisesRegex(WorkflowError, "changed since preview"):
            apply(p, p["approval"])
        self.assertFalse((repo / ".agent-workflow/project.json").exists())

    def test_multi_repo_membership_nested_and_external_worktree(self):
        app = self.repo("space project/app")
        checks = self.repo("space project/checks")
        root = app.parent
        self.setup_project(root)
        nested = app / "src/deep"
        nested.mkdir(parents=True)
        self.assertEqual(resolve(nested).root, root)
        self.assertEqual(resolve(checks).root, root)
        external = self.root / "elsewhere"
        self.git(app, "worktree", "add", "-b", "feature/check", str(external))
        self.assertEqual(resolve(external).root, root)
        unrelated = self.repo("space project/unrelated")
        with self.assertRaises(WorkflowError):
            resolve(unrelated)
        self.assertEqual(self.git(checks, "branch", "--show-current"), "main")

    def test_three_way_keyed_lists_and_conflict_resolution(self):
        base = {"repos": [{"id": "app", "command": "old"}], "deleted": 1}
        current = {"repos": [{"id": "app", "command": "mine"}]}
        detected = {"repos": [{"id": "app", "command": "new"}, {"id": "checks"}], "deleted": 1}
        result, conflicts = merge(base, current, detected)
        self.assertNotIn("deleted", result)
        self.assertEqual(result["repos"][0]["command"], "mine")
        self.assertEqual(result["repos"][1]["id"], "checks")
        self.assertEqual(conflicts[0]["path"], "/repos/app/command")
        result, conflicts = merge(base, current, detected, resolutions={"/repos/app/command": "detected"})
        self.assertFalse(conflicts)
        self.assertEqual(result["repos"][0]["command"], "new")

