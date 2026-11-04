"""Replay the #18 (control-plane) check layout with doubles and report verification time.

Plan evidence for issue #48, not shipped. Usage:

    python3 replay.py PACKAGE_CHECKOUT [as-is|with-when]

PACKAGE_CHECKOUT is a plovi checkout (main, or this branch). The replay builds a throwaway
project whose checks copy the #18 manifest's IDs, phases, identities and argv shapes; each
command is a real unittest module or a sleep that stands in for the tool. The provider double
writes the tests (implement-tests), a broken change (implement), the fix in one same-session
fix round, and nothing in review. "with-when" adds the #48 guidance: focused checks run in the
loop, the full suite and docs tools run once at the end.
"""
import json
import sys
import time
import unittest
from pathlib import Path

PACKAGE = Path(sys.argv[1]).resolve()
VARIANT = sys.argv[2] if len(sys.argv) > 2 else "as-is"
sys.path.insert(0, str(PACKAGE))
from tests.helpers import HardeningTest  # noqa: E402

TEST_SECONDS = 0.02
# Module name, number of tests (from the #18 identities; compatibility modules are typical sizes).
FOCUSED = {"test_ledger": 9, "test_operations": 14, "test_inbox": 8, "test_projects": 4, "test_rebuild_state": 3,
           "test_background_runs": 8, "test_provider_outcomes": 6}
COMPAT = {f"test_compat_{n:02d}": 15 for n in range(1, 13)}
TOOLS = {"generated-docs": 0.3, "plugin-skills": 0.2, "docs-build": 1.0, "links": 0.5, "public-content": 0.6}
REVISION = ["test_rev_a", "test_rev_b", "test_rev_c", "test_rev_d"]


def module(tests):
    body = "".join(f" def test_case_{n}(self): time.sleep({TEST_SECONDS}); self.assertTrue(True)\n" for n in range(tests))
    return f"import time, unittest\nclass Cases(unittest.TestCase):\n{body}"


REVISION_MODULE = "import unittest\nfrom app import VALUE\nclass Revision(unittest.TestCase):\n" + "".join(
    f" def {name}(self): self.assertEqual(VALUE, 2)\n" for name in REVISION)


class Replay(HardeningTest):
    def test_replay(self):
        from plovi import runner, state
        root = self.fixture([{"writes": {"test_revision.py": REVISION_MODULE}}, {"writes": {"app.py": "VALUE = 3\n"}},
                             {"writes": {"app.py": "VALUE = 2\n"}}, {}], stages=["implement-tests", "implement", "review"])
        (root / "test_app.py").write_text(module(1))
        for name, count in {**FOCUSED, **COMPAT}.items():
            (root / f"{name}.py").write_text(module(count))
        self.git(root, "add", "."); self.git(root, "commit", "--quiet", "-m", "Replay modules")
        self.git(root, "push", "--quiet", "origin", "main")
        python = sys.executable
        def unit(name, argv, phases=("green",), identities=(), **extra):
            return {"id": name, "repository": "app", "parser": "unittest", "phases": list(phases), "identities": list(identities),
                    "command": {"argv": [python, "-m", "unittest", "-v", *argv], "timeout_seconds": 300}} | extra
        checks = [unit("control-plane-red", [f"{m}.Cases.test_case_0" for m in list(FOCUSED)[:6]])]
        checks += [unit(m.removeprefix("test_").replace("_", "-"), [m]) for m in FOCUSED]
        checks.insert(6, unit("revision-red", [f"test_revision.Revision.{n}" for n in REVISION], ("red", "green"), REVISION))
        checks.append(unit("compatibility-regressions", list(COMPAT)))
        checks.append({"id": "full-suite", "repository": "app", "parser": "unittest", "phases": ["green"],
                       "command": {"argv": [python, "-m", "unittest", "discover", "-v", "-p", "test_*.py"], "timeout_seconds": 300}})
        for name, seconds in TOOLS.items():
            checks.append({"id": name, "repository": "app", "parser": "generic", "phases": ["green"], "success_pattern": "done",
                           "command": {"argv": [python, "-c", f"import time; time.sleep({seconds}); print('done')"]}})
        if VARIANT == "with-when":
            for check in checks:
                if check["id"] in {"full-suite", "compatibility-regressions", *TOOLS}:
                    check["when"] = ["final"]
                else:
                    check["when"] = ["loop"]
        self.plan["checks"] = checks
        self.plan["outcomes"] = [{"id": "revision", "checks": ["revision-red"]}, {"id": "suite", "checks": ["full-suite"]}]
        self.plan["limits"].update(timeout_seconds=600, inactivity_seconds=300, tool_timeout_seconds=300)
        started = time.monotonic()
        saved = runner.run(self.project, self.plan, unattended=False)
        elapsed = time.monotonic() - started
        assert saved["status"] == "complete", saved.get("error")
        rows = [row for path in sorted((state.directory(self.project, "sample") / "evidence").glob("*.json"))
                for row in json.loads(path.read_text()).get("checks", [])]
        ran = [row for row in rows if not row.get("reused")]
        print(json.dumps({"variant": VARIANT, "run_seconds": round(elapsed, 1),
                          "check_seconds": round(sum(row.get("duration_seconds") or 0 for row in ran), 1),
                          "checks_run": len(ran), "checks_reused": len(rows) - len(ran),
                          "attempts": [a.get("kind") for a in saved["attempts"]]}))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=0, stream=open(__import__("os").devnull, "w")).run(unittest.TestSuite([Replay("test_replay")]))
    if not result.wasSuccessful():
        for _, trace in result.errors + result.failures:
            print(trace, file=sys.stderr)
        sys.exit(1)
