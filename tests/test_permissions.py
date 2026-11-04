import json
from unittest.mock import patch
from tests.helpers import HardeningTest
from plovi import runner, state


class PermissionTests(HardeningTest):
    def restricted(self):
        """Opt into restricted unattended runs; since #47 they use the profile's mode by default."""
        self.policy("execution.unattended_permission_mode", '"restricted"')

    def run_child(self, *flags):
        self.plan["repositories"][0]["branch"] = "feature/sample"
        self.save_plan()
        response = self.task_cli("run", self.manifest_path, *flags)
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        return state.read(self.project, "sample")

    def test_non_tty_restricted_policy_uses_restricted_codex(self):
        self.fixture([{}])
        self.restricted()
        self.run_child()
        argv = self.calls()[0]["argv"]
        self.assertIn("workspace-write", argv)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)

    def test_trusted_flag_is_explicit_and_persisted(self):
        self.fixture([{}])
        saved = self.run_child("--trusted")
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", self.calls()[0]["argv"])
        self.assertIn("--trusted", json.dumps(saved))

    def test_interactive_run_keeps_profile_mode(self):
        self.fixture([{}])
        with patch("sys.stdin.isatty", return_value=True):
            self.assertEqual(runner.run(self.project, self.plan, unattended=False)["status"], "complete")
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", self.calls()[0]["argv"])

    def test_policy_can_explicitly_allow_unattended_trusted(self):
        root = self.fixture([{}])
        self.policy("execution.unattended_permission_mode", '"trusted"')
        self.run_child()
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", self.calls()[0]["argv"])

    def test_cursor_non_tty_uses_enabled_sandbox(self):
        self.fixture([{}])
        self.restricted()
        self.plan["routes"] = {"default": [{"provider": "cursor", "model": "fixture"}]}
        self.project.profile["agents"] = ["cursor"]
        from plovi.util import write_json
        write_json(self.project.config / "project.json", self.project.profile)
        self.run_child()
        argv = self.calls()[0]["argv"]
        self.assertIn("enabled", argv)
        self.assertNotIn("--force", argv)

    def test_claude_derives_narrow_tools_for_configured_checks(self):
        self.fixture([{}])
        self.restricted()
        self.plan["routes"] = {"default": [{"provider": "claude", "model": "fixture"}]}
        self.project.profile["agents"] = ["claude"]
        from plovi.util import write_json
        write_json(self.project.config / "project.json", self.project.profile)
        self.run_child()
        argv = self.calls()[0]["argv"]
        self.assertIn("--allowedTools", argv)
        tools = argv[argv.index("--allowedTools") + 1]
        for tool in ("Read", "Edit", "Write", "Glob", "Grep", "Bash(git status*)", "Bash(git diff*)"):
            self.assertIn(tool, tools)
        self.assertIn("unittest", tools)
        self.assertNotIn("Bash(*)", tools)

    def test_explicit_claude_allowlist_is_preserved(self):
        self.fixture([{}])
        self.restricted()
        self.plan["routes"] = {"default": [{"provider": "claude", "model": "fixture"}]}
        self.project.profile["agents"] = ["claude"]
        self.project.profile["execution"]["provider_settings"] = {"claude": {"allowed_tools": ["Read", "Grep"]}}
        from plovi.util import write_json
        write_json(self.project.config / "project.json", self.project.profile)
        self.run_child()
        argv = self.calls()[0]["argv"]
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Read,Grep")

    def test_unsafe_check_encoding_requires_explicit_claude_tools(self):
        self.fixture([{}])
        self.restricted()
        self.plan["routes"] = {"default": [{"provider": "claude", "model": "fixture"}]}
        self.project.profile["agents"] = ["claude"]
        self.plan["checks"][0]["command"]["argv"] = ["echo", "danger);*"]
        from plovi.util import write_json
        write_json(self.project.config / "project.json", self.project.profile)
        self.save_plan()
        response = self.task_cli("preflight", self.manifest_path)
        self.assertNotEqual(response.returncode, 0)
        self.assertIn("allowed_tools", response.stdout + response.stderr)
        self.assertEqual(self.calls(), [])

    def test_resume_keeps_original_trusted_flag_decision(self):
        self.fixture([{"session": "permission-session", "report": {"status": "needs_input", "question": "Proceed?"}}, {}])
        self.run_child("--trusted")
        answer = self.root / "answer.txt"; answer.write_text("Proceed")
        response = self.task_cli("answer", "sample", "--file", answer)
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        self.assertEqual(len(self.calls()), 2)
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", self.calls()[1]["argv"])

    def test_wrong_claude_account_stops_before_provider_runs(self):
        from types import SimpleNamespace
        from plovi import providers
        from plovi.util import WorkflowError
        root = self.fixture([{}])
        self.plan["routes"] = {"default": [{"provider": "claude", "model": "fixture"}]}
        self.project.profile["agents"] = ["claude"]
        config = self.project.config / "local" / "claude-account.json"
        account = self.root / "personal"; account.mkdir()
        config.write_text(json.dumps({"config_dir": str(account), "email": "personal@example.invalid"}))
        status = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "email": "company@example.invalid"}
        with patch.object(providers, "run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(status))):
            with self.assertRaisesRegex(WorkflowError, "does not match"):
                runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(self.calls(), [])

    def test_wrong_claude_account_blocks_codex_stage_too(self):
        from types import SimpleNamespace
        from plovi import providers
        from plovi.util import WorkflowError
        self.fixture([{}])
        config = self.project.config / "local" / "claude-account.json"
        account = self.root / "personal"; account.mkdir()
        config.write_text(json.dumps({"config_dir": str(account), "email": "personal@example.invalid"}))
        status = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "email": "company@example.invalid"}
        with patch.object(providers, "run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(status))):
            with self.assertRaisesRegex(WorkflowError, "does not match"):
                runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(self.calls(), [])

    def test_personal_claude_configuration_reaches_codex_stage(self):
        import os
        from plovi import providers
        self.fixture([{}])
        selected = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.root / "personal"))
        with patch.object(providers, "claude_environment", return_value=selected), \
             patch.object(runner, "execute_process", wraps=runner.execute_process) as execute:
            result = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(execute.call_args.kwargs["env"]["CLAUDE_CONFIG_DIR"], selected["CLAUDE_CONFIG_DIR"])
