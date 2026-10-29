"""Behavioral requirements added by the updated rebrand issue."""
from __future__ import annotations
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import warnings
from tests.helpers import PACKAGE, WorkspaceTest
from plovi import install
from plovi.util import read_json, write_json, user_data

class RebrandRevisionTests(WorkspaceTest):
    def test_canonical_project_wins_and_legacy_data_is_preserved(self):
        root = self.repo("app")
        project = self.setup_project(root)
        legacy = root / ".agentflow"; legacy.mkdir()
        (legacy / "project.json").write_text((project.config / "project.json").read_text())
        (legacy / "keep.bin").write_bytes(b"legacy\0data")
        data = read_json(project.config / "project.json")
        data["tracking"]["provider"] = "linear"
        write_json(project.config / "project.json", data)
        result = self.cli("inspect", cwd=root, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["profile"]["tracking"]["provider"], "linear")
        self.assertIn("using .plovi/", result.stderr)
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assertEqual((legacy / "keep.bin").read_bytes(), b"legacy\0data")

    def test_stale_run_state_does_not_block_migration(self):
        root = self.repo("app")
        project = self.setup_project(root)
        project.config.rename(root / ".agentflow")
        state = root / ".agentflow/local/evidence/stale/state.json"
        state.parent.mkdir(parents=True)
        state.write_text('{"status":"running"}')
        result = self.cli("inspect", cwd=root, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("(one-time rename)", result.stderr)
        self.assertEqual((root / ".plovi/local/evidence/stale/state.json").read_text(), '{"status":"running"}')

    def test_held_run_lock_refuses_without_changing_configuration(self):
        from plovi.state import lock
        root = self.repo("app")
        project = self.setup_project(root)
        project.config.rename(root / ".agentflow")
        state = root / ".agentflow/local/evidence/live/state.json"
        state.parent.mkdir(parents=True)
        state.write_text('{"status":"starting"}')
        with lock(root / ".agentflow/local/runner.lock"):
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = self.cli("inspect", cwd=root, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})
        self.assertFalse((root / ".plovi").exists())

    def test_internal_git_worktree_is_repaired_after_migration(self):
        root = self.repo("app")
        project = self.setup_project(root)
        self.git(root, "add", "."); self.git(root, "commit", "-m", "Configure fixture")
        project.config.rename(root / ".agentflow")
        data = read_json(root / ".agentflow/project.json")
        data["git"]["worktree_directory"] = ".agentflow/local/worktrees"
        write_json(root / ".agentflow/project.json", data)
        old = root / ".agentflow/local/worktrees/task"
        old.parent.mkdir(parents=True)
        self.git(root, "worktree", "add", "-b", "task/sample", str(old))
        result = self.cli("inspect", cwd=root, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        moved = root / ".plovi/local/worktrees/task"
        listing = self.git(root, "worktree", "list", "--porcelain")
        self.assertIn(str(moved), listing)
        self.assertNotIn(str(old), listing)
        self.assertEqual(self.git(moved, "branch", "--show-current"), "task/sample")
        common = self.git(moved, "rev-parse", "--git-common-dir")
        self.assertTrue(common)

    def test_user_data_migrates_from_each_legacy_name_once(self):
        for name in ("agentflow", "agent-workflow"):
            with self.subTest(name=name):
                base = self.home / ("data-" + name)
                legacy = base / name; legacy.mkdir(parents=True)
                (legacy / "models").mkdir()
                settings = legacy / "models/settings.json"
                settings.write_bytes(b'{"schema_version":1,"custom":"unchanged"}')
                with warnings.catch_warnings(), contextlib.redirect_stderr(io.StringIO()) as output:
                    with __import__('unittest').mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(base)}):
                        current = user_data()
                        self.assertEqual(current, base / "plovi")
                        self.assertFalse(legacy.exists())
                        self.assertEqual((current / "models/settings.json").read_bytes(), settings.read_bytes() if settings.exists() else b'{"schema_version":1,"custom":"unchanged"}')
                        notice = output.getvalue()
                        self.assertIn("plovi", notice)
                        self.assertEqual(user_data(), current)
                        self.assertEqual(output.getvalue(), notice)

    def test_legacy_python_import_warns_and_reexports_version(self):
        result = subprocess.run([sys.executable, "-Walways", "-c",
                                 "import sys;sys.path.insert(0,'runtime');import agentflow,plovi;assert agentflow.__version__==plovi.__version__"],
                                cwd=PACKAGE, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DeprecationWarning", result.stderr)

    def test_legacy_source_marker_is_accepted_for_compatibility_release(self):
        source = self.root / "legacy-source"
        for path in install.files_in(PACKAGE):
            dest = source / path.relative_to(PACKAGE); dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        marker = read_json(source / "workflow-package.json"); marker["name"] = "agentflow"
        write_json(source / "workflow-package.json", marker)
        error = None
        try:
            install.validate_source(source)
        except Exception as exc:
            error = str(exc)
        self.assertIsNone(error, "legacy source markers must remain compatible: " + str(error))

    def test_alias_descriptions_identify_the_replacement(self):
        generated = install.wrappers(PACKAGE, None, ["codex", "claude", "cursor"])
        aliases = [content for path, content in generated.items() if path.name == "SKILL.md" and path.parent.name.startswith("af-")]
        self.assertEqual(len(aliases), 2 * len(install.catalog(package=PACKAGE)))
        self.assertTrue(all('description: "Deprecated alias of plovi-' in text for text in aliases))

    def test_old_package_environment_variable_still_resolves(self):
        root = self.repo("app"); self.setup_project(root)
        env = {k:v for k,v in self.env.items() if k != "PLOVI_PACKAGE"}
        env["AGENTFLOW_PACKAGE"] = str(PACKAGE)
        result = subprocess.run([sys.executable, str(PACKAGE / "skills/review/scripts/resolve.py")], cwd=root,
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(PACKAGE / "skills/review/SKILL.md"))

    def test_global_install_preview_does_not_move_user_data(self):
        legacy = self.home / "data/agentflow"
        legacy.mkdir(parents=True)
        (legacy / "settings.bin").write_bytes(b"keep\0unchanged")
        result = install.install(PACKAGE, dry_run=True)
        self.assertTrue(legacy.exists(), "preview must not move user data")
        self.assertFalse((self.home / "data/plovi").exists())
        self.assertIn("migration", result)
        self.assertEqual((legacy / "settings.bin").read_bytes(), b"keep\0unchanged")

    def test_profile_prefix_paths_rebase_without_editing_embedded_prose(self):
        root = self.repo("app"); project = self.setup_project(root)
        project.config.rename(root / ".agentflow")
        path = root / ".agentflow/project.json"
        data = read_json(path)
        data["custom_extension"] = {"path": ".agentflow/references/example", "text": "keep .agentflow/references/example in this note"}
        write_json(path, data)
        result = self.cli("inspect", cwd=root, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        custom = json.loads(result.stdout)["profile"]["custom_extension"]
        self.assertEqual(custom["path"], ".plovi/references/example")
        self.assertEqual(custom["text"], data["custom_extension"]["text"])

    def test_installing_an_actual_legacy_payload_uses_current_bootstrap(self):
        source = self.root / "legacy-payload"
        (source / "runtime/agentflow").mkdir(parents=True)
        (source / "runtime/agentflow/__init__.py").write_text('')
        (source / "runtime/agentflow/cli.py").write_text('def main(args):\n    print("legacy-runtime")\n    return 0\n')
        (source / "bin").mkdir(); (source / "bin/agentflow").write_text('# legacy launcher\n')
        skill = source / "skills/project-setup/SKILL.md"; skill.parent.mkdir(parents=True)
        skill.write_text('---\nname: project-setup\ndescription: Fixture setup\n---\nFixture.\n')
        write_json(source / "workflow-package.json", {"name":"agentflow","version":"0.0.9","schema_version":1,"discovery":{"prefix":"af"}})
        result = install.install(source)
        self.assertFalse(result["conflicts"])
        env = {k:v for k,v in self.env.items() if k != "PLOVI_PACKAGE"}
        check = subprocess.run([sys.executable, str(self.home / ".local/bin/plovi"), "--version"],
                               cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(check.stdout.strip(), "legacy-runtime")

    def test_migrating_user_data_keeps_late_imports_from_a_moved_payload_working(self):
        legacy = self.home / "data/agentflow"
        package = legacy / "versions/old/runtime/fixture_live_payload"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text('')
        (package / "later.py").write_text('value = "late import survived"\n')
        code = "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);sys.path.insert(0,'runtime');import fixture_live_payload;from plovi.util import user_data;user_data();from fixture_live_payload.later import value;assert value=='late import survived'"
        result = subprocess.run([sys.executable, "-c", code, str(package.parent)], cwd=PACKAGE,
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_project_only_skill_survives_moving_its_selected_payload(self):
        root = self.repo("app")
        install.install(PACKAGE, project=root)
        self.setup_project(root)
        (root / ".plovi").rename(root / ".agentflow")
        for relative in ("project.json", "runtime/active.json", "runtime/receipt.json", "local/setup-baseline.json"):
            path = root / ".agentflow" / relative
            path.write_text(path.read_text().replace(".plovi", ".agentflow"))
        env = {k:v for k,v in self.env.items() if k != "PLOVI_PACKAGE"}
        result = subprocess.run([sys.executable, str(root / ".agents/skills/plovi-review/scripts/dispatch.py")],
                                cwd=root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = root / ".plovi/runtime/versions" / read_json(PACKAGE / "workflow-package.json")["version"] / "skills/review/SKILL.md"
        self.assertEqual(result.stdout.strip(), str(expected))
