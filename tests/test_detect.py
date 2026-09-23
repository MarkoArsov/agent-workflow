from __future__ import annotations
from tests.helpers import WorkspaceTest
from agent_workflow.detect import scan

class DetectorTests(WorkspaceTest):
    def test_stack_and_branch_detection_uses_static_repository_facts(self):
        cases = [
            ("node", {"package.json": '{"scripts":{"test":"vitest run"}}', "pnpm-lock.yaml": ""}, ["pnpm", "run", "test"], "jest"),
            ("dotnet", {"App.sln": ""}, ["dotnet", "test", "App.sln"], "dotnet"),
            ("go", {"go.mod": "module example.invalid/app\n"}, ["go", "test", "-v", "./..."], "go"),
            ("rust", {"Cargo.toml": '[package]\nname = "fixture"\n'}, ["cargo", "test"], "rust"),
            ("make", {"Makefile": "test:\n\t@echo complete\n"}, ["make", "test"], "generic"),
            ("task", {"Taskfile.yml": 'version: "3"\ntasks:\n  test:\n    cmds: [echo complete]\n'}, ["task", "test"], "generic")]
        for name, files, argv, parser in cases:
            with self.subTest(stack=name):
                root = self.repo(name)
                for path, body in files.items():
                    (root / path).write_text(body)
                self.git(root, "update-ref", "refs/remotes/origin/release", "HEAD")
                self.git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/release")
                detected = scan(root)
                repo = detected["profile"]["repositories"][0]
                self.assertEqual(repo["base_branch"], "release")
                self.assertEqual(repo["commands"]["test"]["argv"], argv)
                self.assertEqual(repo["commands"]["test"]["parser"], parser)
                self.assertEqual(self.git(root, "branch", "--show-current"), "main")
