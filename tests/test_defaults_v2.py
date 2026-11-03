"""New-task defaults (#47): permission mode, checkouts, runtime pin, state version, task base and the account guard."""
from tests.helpers import HardeningTest, WorkspaceTest
from plovi import state
from plovi.util import WorkflowError


class StateVersionTests(WorkspaceTest):
    def test_state_version_migrates_forward(self):
        old = {"schema_version": 1, "task": "sample", "status": "failed", "completed": ["implement"]}
        migrated = state.migrate(old)
        self.assertEqual(migrated["state_version"], state.STATE_VERSION)
        self.assertEqual((migrated["attempts"], migrated["delivery"], migrated["stage_evidence"]), ([], {}, {}))
        self.assertEqual(migrated["completed"], ["implement"])
        self.assertIs(state.migrate(migrated), migrated)
        with self.assertRaisesRegex(WorkflowError, "state version 9.*newer plovi"):
            state.migrate({"state_version": 9})


class PermissionDefaultTests(HardeningTest):
    def run_child(self):
        self.plan["repositories"][0]["branch"] = "feature/sample"
        self.save_plan()
        response = self.task_cli("run", self.manifest_path)
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        return state.read(self.project, "sample")

    def test_unattended_uses_profile_permission_mode(self):
        self.fixture([{}])
        saved = self.run_child()
        self.assertEqual((saved["execution"]["permission_mode"], saved["execution"]["permission_source"]),
                         ("trusted", "unattended default (profile)"))
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", self.calls()[0]["argv"])

    def test_restricted_still_selectable(self):
        self.fixture([{}])
        (self.project.root / "plovi.toml").write_text('[execution]\nunattended_permission_mode = "restricted"\n')
        saved = self.run_child()
        self.assertEqual((saved["execution"]["permission_mode"], saved["execution"]["permission_source"]), ("restricted", "policy"))
        self.assertIn("workspace-write", self.calls()[0]["argv"])
