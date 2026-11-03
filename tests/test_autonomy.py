"""Challenging premature stops (#47): the stop list, recoverable categories and same-session continuation."""
import unittest
import tests.helpers  # noqa: F401  (puts runtime/ on sys.path)
from plovi import autonomy, providers

COMMANDS = ["python3 -m unittest -v test_app", "npm run build", "python3 scripts/generate_client.py"]

# (reason, stage, expected category or None) from the issue's table; None means "not recoverable".
MUST_MATCH = [
    ("network timeout while installing packages", "implement", "transient"),
    ("connection reset by peer", "implement", "transient"),
    ("the package registry unavailable right now", "implement", "transient"),
    ("Docker daemon not running", "implement", "transient"),
    ("rate limited, retry after 30s", "implement", "transient"),
    ("I need to run the generator before the tests compile", "implement", "project-command"),
    ("This requires running `npm run build` first", "implement", "project-command"),
    ("We must regenerate the lockfile", "implement", "project-command"),
    ("The generated client is out of date", "implement", "generated-code"),
    ("The proxy needs regeneration", "implement", "generated-code"),
    ("The test helper returns null for the new field", "implement", "test-fixture"),
    ("The fixture is missing a field", "review", "test-fixture"),
    ("The test does not compile because a member was renamed", "implement", "test-fixture"),
    ("The review should handle the docs wording", "implement", "later-stage"),
    ("The commit stage will include the changelog", "implement", "later-stage"),
    ("I need permission to delete a temporary file", "implement", "local-permission"),
    ("Should I run the tests?", "implement", "local-permission"),
]
MUST_NOT_MATCH = [
    ("usage limit reached", "implement"),
    ("This requires running `curl https://example.invalid/setup.sh` first", "implement"),
    ("The test asserts the wrong behaviour", "implement"),
    ("The fixture is missing a field", "implement-tests"),
    ("Should I push the branch?", "implement"),
    ("Can I merge this into main?", "implement"),
    ("Do I need to deploy before testing?", "implement"),
    ("I need permission to read the production database", "implement"),
    ("I need the deploy credentials", "implement"),
]


class CategoryTests(unittest.TestCase):
    def test_category_table_examples(self):
        for reason, stage, expected in MUST_MATCH:
            with self.subTest(reason=reason):
                self.assertEqual(autonomy.classify_stop(reason, stage=stage, commands=COMMANDS), ("recoverable", expected))
        for reason, stage in MUST_NOT_MATCH:
            with self.subTest(reason=reason):
                self.assertNotEqual(autonomy.classify_stop(reason, stage=stage, commands=COMMANDS)[0], "recoverable")

    def test_stop_list_keys_are_recognised(self):
        examples = {
            "behaviour": "The test asserts the wrong behaviour; which outcome do users expect?",
            "public-contract": "This is a breaking change to the public API",
            "data-loss": "The migration irreversibly deletes user data",
            "security": "This changes the authentication rules",
            "money": "This touches billing and pricing",
            "external-action": "I need access to an external account to continue",
            "oversize": "This is too large for one change and should be split",
            "untrusted-author": "The issue text tells me to ignore previous instructions",
            "undeclared-protected-path": "I need to edit a protected path the plan does not list",
        }
        self.assertEqual(set(examples), set(autonomy.STOP_LIST))
        for key, reason in examples.items():
            with self.subTest(key=key):
                self.assertEqual(autonomy.classify_stop(reason, stage="implement", commands=COMMANDS), ("stop", key))

    def test_stop_marker_wins_over_keywords(self):
        # The keywords say "transient", the marker says money: the marker decides, and a stop is never challenged.
        reason = "network timeout while checking the price list [stop:money]"
        self.assertEqual(autonomy.classify_stop(reason, stage="implement", commands=COMMANDS), ("stop", "money"))
        self.assertEqual(autonomy.classify_stop("network timeout [stop:unknown-key]", stage="implement", commands=COMMANDS),
                         ("recoverable", "transient"))

    def test_unmatched_reason_is_a_question(self):
        self.assertEqual(autonomy.classify_stop("Which colour should the button be?", stage="implement", commands=COMMANDS),
                         ("question", None))

    def test_challenge_prompt_redacts_and_names_the_stage(self):
        prompt = autonomy.challenge_prompt("network timeout with token=sk-live-0123456789abcdef0123", "implement")
        self.assertIn("Your previous stop was premature:", prompt)
        self.assertNotIn("sk-live-0123456789abcdef0123", prompt)
        self.assertTrue(prompt.rstrip().endswith("PLOVI_STAGE_OK: implement"))

    def test_backoff_doubles_and_caps(self):
        self.assertEqual([autonomy.backoff(n, environ={}) for n in (1, 2, 3, 4, 5, 6)], [20, 40, 80, 160, 300, 300])
        self.assertEqual(autonomy.backoff(3, environ={"PLOVI_CHALLENGE_BACKOFF_SECONDS": "0"}), 0)

    def test_loop_checks_are_the_green_checks_until_48(self):
        manifest = {"checks": [{"id": "red-only", "phases": ["red"]}, {"id": "behavior", "phases": ["red", "green"]},
                               {"id": "lint"}]}
        self.assertEqual([c["id"] for c in autonomy.loop_checks(manifest)], ["behavior", "lint"])


class ResumeArgvTests(unittest.TestCase):
    def test_resume_argv_per_provider(self):
        execution = {"permission_mode": "trusted"}
        codex = providers.command({"provider": "codex", "model": "m"}, execution, session="S1", prompt="p")
        self.assertEqual(codex[:3], ["codex", "exec", "resume"])
        self.assertEqual(codex[-2:], ["S1", "-"])
        claude = providers.command({"provider": "claude", "model": "m"}, execution, session="S2", prompt="p")
        self.assertEqual(claude[claude.index("--resume") + 1], "S2")
        cursor = providers.command({"provider": "cursor", "model": "m"}, execution, session="S3", prompt="p")
        self.assertEqual(cursor[cursor.index("--resume") + 1], "S3")
        self.assertEqual(cursor[-1], "p")
