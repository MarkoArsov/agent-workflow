"""Provider availability and circuits (#47): only installed providers are proposed or run, and permanent failures skip a provider."""
import shutil
from unittest.mock import patch
from tests.helpers import HardeningTest
from plovi import ledger, runner
from plovi.util import WorkflowError

ROUTES = {"default": [{"provider": "codex", "model": "primary"}, {"provider": "claude", "model": "fallback"}]}


class AvailabilityTests(HardeningTest):
    def both(self, steps, **kwargs):
        self.fixture(steps, **kwargs)
        self.plan["routes"] = ROUTES
        self.project.profile["agents"] = ["codex", "claude"]

    def without(self, *missing):
        real = shutil.which
        names = {"codex": "codex", "claude": "claude", "cursor": "agent"}
        blocked = {names[p] for p in missing}
        return patch("shutil.which", side_effect=lambda cmd, *a, **k: None if cmd in blocked else real(cmd, *a, **k))

    def test_evaluator_proposes_only_installed_providers(self):
        from plovi import model_routing
        self.fixture([{}])
        self.project.profile["agents"] = ["codex", "claude", "cursor"]
        self.project.profile["pipeline"]["routes"] = {"default": [{"provider": "codex", "model": "primary"},
                                                                  {"provider": "claude", "model": "fallback"}]}
        import argparse, json
        from plovi.model_policy.commands import arguments, execute
        facts = self.root / "facts.json"
        facts.write_text(json.dumps({"stages": ["implement"], "kind": "code", "size": "small",
                                     "risk": "standard", "uncertain": False}))
        parser = argparse.ArgumentParser(); arguments(parser)
        args = parser.parse_args(["evaluate", "--input", str(facts), "--verbose"])
        with self.without("claude", "cursor"):
            result = execute(args, model_routing.store(self.project), self.project.root)
        self.assertTrue(result["routes"]["implement"])
        self.assertIn({"stage": "implement", "reason": "uninstalled-provider-skipped"}, result["advisories"])
        providers = {route["provider"] for routes in result["routes"].values() for route in routes}
        self.assertNotIn("claude", providers)
        self.assertNotIn("cursor", providers)

    def test_missing_provider_route_skipped_with_warning(self):
        import contextlib, io
        self.both([{}])
        warning = io.StringIO()
        with self.without("codex"), contextlib.redirect_stderr(warning):
            saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(saved["status"], "complete")
        self.assertIn("Skipping codex/primary for implement: codex is not installed", warning.getvalue())
        self.assertEqual({a["route"]["provider"] for a in saved["attempts"]}, {"claude"})

    def test_no_route_left_fails_preflight(self):
        self.both([{}])
        with self.without("codex", "claude"), self.assertRaisesRegex(WorkflowError, "No installed provider for implement"):
            runner.preflight(self.project, self.plan)

    def test_permanent_failure_opens_provider_circuit(self):
        self.both([{"auth_failure": True}, {}, {}], stages=["implement", "review"])
        saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(saved["status"], "complete")
        self.assertEqual([a["route"]["provider"] for a in saved["attempts"]], ["codex", "claude", "claude"])
        opened = [e["data"] for e in ledger.events(self.project) if e["type"] == "provider.circuit_open"]
        self.assertEqual([(d["provider"], d["classification"]) for d in opened], [("codex", "authentication")])
