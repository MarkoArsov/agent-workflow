from tests.helpers import WorkspaceTest
from agent_workflow.providers import command, Events
from agent_workflow.util import WorkflowError
import json

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

