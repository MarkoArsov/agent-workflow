from __future__ import annotations
import os
import selectors
import shutil
import subprocess
import sys
from tests.helpers import PACKAGE, WorkspaceTest
from scorebook.project import resolve
from scorebook.setup import propose

class ExecutableFixtureTests(WorkspaceTest):
    def fixture(self, name, source):
        root = self.repo(name)
        shutil.copytree(PACKAGE / "tests/fixtures" / source, root, dirs_exist_ok=True)
        (root / ".gitignore").write_text("__pycache__/\n")
        self.git(root, "add", "."); self.git(root, "commit", "-m", "Add executable fixture")
        return root

    def test_single_repo_runs_and_nested_detection_works(self):
        root = self.fixture("single", "single-repo")
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                                cwd=root, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("test_greeting", result.stderr)
        self.assertEqual(propose(root / "tests")["root"], str(root))

    def test_multi_repo_e2e_calls_disposable_app_without_modifying_checks(self):
        app = self.fixture("multi/app", "multi-repo/app")
        checks = self.fixture("multi/checks", "multi-repo/checks")
        project = self.setup_project(app.parent)
        for repo in (app, checks):
            self.git(repo, "add", "."); self.git(repo, "commit", "-m", "Configure project")
        head = self.git(checks, "rev-parse", "HEAD")
        server = subprocess.Popen([sys.executable, "server.py"], cwd=app, env=self.env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if server.poll() is None:
                server.kill(); server.wait(timeout=5)
            server.stdout.close(); server.stderr.close()
        self.addCleanup(cleanup)
        selector = selectors.DefaultSelector(); selector.register(server.stdout, selectors.EVENT_READ)
        self.assertTrue(selector.select(5), "Application did not report readiness")
        port = server.stdout.readline().strip()
        if not port.isdigit():
            self.fail("Application failed to start: " + server.stderr.read())
        env = dict(self.env, SAMPLE_BASE_URL="http://127.0.0.1:" + port)
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                                cwd=checks, env=env, text=True, capture_output=True)
        server.terminate(); server.wait(timeout=5)
        server.stdout.close(); server.stderr.close(); selector.close()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("test_readiness", result.stderr)
        self.assertEqual(self.git(checks, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(checks, "status", "--porcelain"), "")
        self.assertEqual(self.git(checks, "branch", "--show-current"), "main")
        self.assertEqual(resolve(checks / "tests").root, project.root)
