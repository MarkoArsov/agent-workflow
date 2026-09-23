from __future__ import annotations
import shutil
import sys
from tests.helpers import PACKAGE, WorkspaceTest
from agent_workflow import environments, verification
from agent_workflow.util import WorkflowError

class EnvironmentTests(WorkspaceTest):
    def fixture(self):
        app = self.repo("workspace/app"); checks = self.repo("workspace/checks")
        shutil.copytree(PACKAGE / "tests/fixtures/multi-repo/app", app, dirs_exist_ok=True)
        shutil.copytree(PACKAGE / "tests/fixtures/multi-repo/checks", checks, dirs_exist_ok=True)
        project = self.setup_project(app.parent)
        project.profile["environments"] = {"sample": {"lock_id": "sample-shared-app", "services": [
            {"id": "server", "repository": "app", "command": {"argv": [sys.executable, "server.py"]},
             "ready_pattern": r"^(?P<port>[0-9]+)$", "exports": {"SAMPLE_BASE_URL": "http://127.0.0.1:{port}"}, "startup_timeout_seconds": 15}]}}
        paths = {"app": str(app), "checks": str(checks)}
        return project, paths

    def test_readiness_export_check_and_owned_cleanup(self):
        project, paths = self.fixture()
        plan = {"checks": [{"id": "http", "repository": "checks", "environment": "sample",
                           "parser": "unittest", "identities": ["test_readiness"],
                           "command": {"argv": [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                                       "env_refs": ["SAMPLE_BASE_URL"], "timeout_seconds": 10}}]}
        result = verification.run_checks(project, plan, paths)
        self.assertTrue(result[0]["passed"], result)
        self.assertEqual(environments.status(project, "sample")["status"], "released")

    def test_shared_lease_and_release_request(self):
        project, paths = self.fixture()
        with environments.lease(project, "sample", paths) as (exported, cancelled):
            self.assertIn("SAMPLE_BASE_URL", exported)
            self.assertEqual(environments.status(project, "sample")["status"], "active")
            with self.assertRaisesRegex(WorkflowError, "lock"):
                with environments.lease(project, "sample", paths):
                    pass
            self.assertFalse(cancelled())
            self.assertTrue(environments.release(project, "sample")["release_requested"])
            self.assertTrue(cancelled())
        self.assertEqual(environments.status(project, "sample")["status"], "released")

    def test_failed_startup_releases_owned_process(self):
        project, paths = self.fixture()
        service = project.profile["environments"]["sample"]["services"][0]
        service["command"]["argv"] = [sys.executable, "-c", "print('not ready')"]
        with self.assertRaisesRegex(WorkflowError, "before readiness"):
            with environments.lease(project, "sample", paths):
                pass
        self.assertEqual(environments.status(project, "sample")["status"], "released")
