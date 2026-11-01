from tests.helpers import WorkspaceTest
from plovi.providers import command, Events
from plovi.util import WorkflowError
import json
import os
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

class ProviderTests(WorkspaceTest):
    def test_initial_resume_and_permission_modes(self):
        for provider in ("codex", "claude", "cursor"):
            route = {"provider": provider, "model": "chosen-model"}
            trusted = {"permission_mode": "trusted"}
            restricted = {"permission_mode": "restricted", "provider_settings": {"claude": {"allowed_tools": ["Read", "Edit"]}}}
            for session in (None, "exact-session"):
                with self.subTest(provider=provider, session=session):
                    argv = command(route, trusted, session=session, prompt="prompt")
                    self.assertIn("chosen-model", argv)
                    if session:
                        self.assertIn(session, argv)
                    restricted_argv = command(route, restricted, session=session, prompt="prompt")
                    self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", restricted_argv)
                    self.assertNotIn("--dangerously-skip-permissions", restricted_argv)
                    self.assertNotIn("--force", restricted_argv)
        with self.assertRaisesRegex(WorkflowError, "allowed_tools"):
            command({"provider": "claude", "model": "chosen"}, {"permission_mode": "restricted"})

    def test_provider_result_and_unknown_usage(self):
        events = Events()
        events.line(json.dumps({"type": "result", "session_id": "same-session",
                                "result": '{"status":"needs_input","question":"Choose?"}'}))
        self.assertEqual(events.report()["status"], "needs_input")
        self.assertEqual(events.session, "same-session")
        self.assertIsNone(events.cost_usd)
        self.assertIsNone(events.usage)


    def test_result_accepts_terminal_fenced_json_after_prose(self):
        events = Events()
        events.line(json.dumps({"type": "result", "result": 'Completed the checks.\n\n```json\n{"status":"complete","summary":"done"}\n```'}))
        self.assertEqual(events.report(), {"status": "complete", "summary": "done"})

    def test_nonterminal_or_invalid_fenced_reports_are_not_accepted(self):
        for text in ('```json\n{"status":"complete"}\n```\nAdditional text',
                     'Summary\n```json\n{"status":"needs_input"}\n```',
                     'Summary with {"status":"complete"} inline'):
            with self.subTest(text=text):
                events = Events()
                events.line(json.dumps({"type": "result", "result": text}))
                self.assertIsNone(events.report())

    def test_configured_claude_identity_is_verified_and_forwarded(self):
        from plovi import providers
        self.assertTrue(hasattr(providers, "claude_environment"))
        project = SimpleNamespace(config=self.root / "project")
        config = project.config / "local" / "claude-account.json"
        config.parent.mkdir(parents=True)
        account = self.root / "personal"; account.mkdir()
        config.write_text(json.dumps({"config_dir": str(account), "email": "person@example.invalid"}))
        status = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "email": "person@example.invalid"}
        with patch.object(providers, "run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(status))) as probe:
            env = providers.claude_environment(project, self.root)
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], str(account))
        self.assertEqual(probe.call_args.kwargs["env"]["CLAUDE_CONFIG_DIR"], str(account))

    def test_claude_guard_refuses_wrong_identity_and_override_credentials(self):
        from plovi import providers
        self.assertTrue(hasattr(providers, "claude_environment"))
        project = SimpleNamespace(config=self.root / "project")
        config = project.config / "local" / "claude-account.json"
        config.parent.mkdir(parents=True)
        account = self.root / "personal"; account.mkdir()
        config.write_text(json.dumps({"config_dir": str(account), "email": "person@example.invalid"}))
        status = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "email": "other@example.invalid"}
        with patch.object(providers, "run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(status))):
            with self.assertRaises(WorkflowError): providers.claude_environment(project, self.root)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fixture-secret"}):
            with self.assertRaises(WorkflowError): providers.claude_environment(project, self.root)

    def test_missing_required_claude_guard_fails_closed(self):
        from plovi import providers
        project = SimpleNamespace(config=self.root / "project")
        local = project.config / "local"; local.mkdir(parents=True)
        (local / "claude-account.required").touch()
        with self.assertRaisesRegex(WorkflowError, "required"):
            providers.claude_environment(project, self.root)

    def test_last_fenced_report_wins_after_earlier_examples(self):
        events = Events()
        text = 'Example:\n```json\n{"other":true}\n```\nFinal:\n```json\n{"status":"complete"}\n```'
        events.line(json.dumps({"type": "result", "result": text}))
        self.assertEqual(events.report(), {"status": "complete"})

    def test_invalid_final_result_cannot_reuse_earlier_report(self):
        events = Events()
        events.line(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": '{"status":"complete"}'}}))
        events.line(json.dumps({"type": "result", "result": 'Final answer without a report'}))
        self.assertIsNone(events.report())
