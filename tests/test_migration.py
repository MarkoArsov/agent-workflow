"""Lossless project migration and its legacy compatibility contracts."""
from __future__ import annotations
import contextlib
import importlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from tests.helpers import PACKAGE, WorkspaceTest

RUNTIME = "plovi" if (PACKAGE / "runtime/plovi").exists() else "agentflow"

class MigrationTests(WorkspaceTest):
    def legacy(self, name="app"):
        root = self.repo(name)
        self.setup_project(root)
        current, legacy = root / ".plovi", root / ".agentflow"
        if current.exists():
            current.rename(legacy)
            for file in (legacy / "project.json", legacy / "local/setup-baseline.json"):
                file.write_text(file.read_text().replace(".plovi", ".agentflow").replace("<!-- plovi:", "<!-- agentflow:"))
        custom = legacy / "custom/sub/data.bin"
        custom.parent.mkdir(parents=True)
        custom.write_bytes(b"\x00arbitrary user content\xff")
        custom.chmod(0o600)
        return root

    def run_cli(self, root, *args):
        command = PACKAGE / "bin/plovi"
        if not command.exists():
            command = PACKAGE / "bin/agentflow"
        return subprocess.run([sys.executable, str(command), *args], cwd=root, env=self.env,
                              text=True, capture_output=True)

    def migration(self):
        spec = importlib.util.find_spec(RUNTIME + ".migration")
        self.assertIsNotNone(spec, "migration must be implemented")
        return importlib.import_module(RUNTIME + ".migration")

    def test_legacy_project_moves_without_data_loss(self):
        root = self.legacy()
        result = self.run_cli(root, "inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        moved = root / ".plovi/custom/sub/data.bin"
        self.assertTrue(moved.is_file(), "first applicable run must move the project folder")
        self.assertEqual(moved.read_bytes(), b"\x00arbitrary user content\xff")
        if os.name != "nt":
            self.assertEqual(moved.stat().st_mode & 0o777, 0o600)
        self.assertFalse((root / ".agentflow").exists())
        self.assertEqual(result.stderr.count("Moved .agentflow/ to .plovi/"), 1)

    def test_repeat_run_does_not_repeat_notice(self):
        root = self.legacy()
        first = self.run_cli(root, "inspect")
        second = self.run_cli(root, "inspect")
        self.assertEqual(first.stderr.count("Moved .agentflow/ to .plovi/"), 1)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stderr, "")

    def test_rebased_profile_and_receipt_remain_usable(self):
        root = self.legacy()
        install = importlib.import_module(RUNTIME + ".install")
        # Install into the legacy tree before invoking the migration.
        self.migration()
        result = self.run_cli(root, "inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        install.install(PACKAGE, project=root)
        receipt = json.loads((root / ".plovi/runtime/receipt.json").read_text())
        self.assertTrue(all(".agentflow" not in key for key in receipt["files"]))
        profile = json.loads((root / ".plovi/project.json").read_text())
        self.assertEqual(profile["extensions"]["skills"], ".plovi/skills")
        self.assertEqual(profile["planning"]["evidence_directory"], ".plovi/local/evidence")
        again = importlib.import_module(RUNTIME + ".setup").propose(root)
        self.assertFalse(again["conflicts"])

    def test_both_directories_preserved_on_conflict(self):
        root = self.legacy()
        (root / ".plovi").mkdir()
        (root / ".plovi/keep").write_text("keep")
        before = (root / ".agentflow/project.json").read_bytes()
        result = self.run_cli(root, "inspect")
        self.assertNotEqual(result.returncode, 0, "ambiguous folders must stop")
        self.assertEqual((root / ".agentflow/project.json").read_bytes(), before)
        self.assertEqual((root / ".plovi/keep").read_text(), "keep")

    def test_preview_does_not_migrate(self):
        root = self.legacy()
        result = self.run_cli(root, "setup", "--output", str(self.root / "proposal.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((root / ".agentflow/project.json").is_file())
        self.assertFalse((root / ".plovi").exists())
        self.assertIn("migration", (self.root / "proposal.json").read_text().lower())

    def test_unrelated_project_is_not_migrated(self):
        root = self.legacy("workspace/app")
        unrelated = self.repo("workspace/app/unrelated")
        result = self.run_cli(unrelated, "inspect")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((root / ".agentflow").is_dir())
        self.assertFalse((root / ".plovi").exists())

    def test_interruption_recovers_without_loss(self):
        migration = self.migration()
        root = self.legacy()
        real_write = migration.atomic_write
        for phase in ("before-move", "after-move", "metadata"):
            def fail(label):
                if label == phase:
                    raise RuntimeError("simulated interruption")
            with patch.object(migration, "checkpoint", side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, "interruption"):
                    migration.migrate(root)
            migration.migrate(root)
            self.assertEqual((root / ".plovi/custom/sub/data.bin").read_bytes(), b"\x00arbitrary user content\xff")
            if phase != "metadata":
                # Recreate a legacy configuration for the next fault boundary.
                (root / ".plovi").rename(root / ".agentflow")
                for file in (root / ".agentflow/project.json", root / ".agentflow/local/setup-baseline.json"):
                    file.write_text(file.read_text().replace(".plovi", ".agentflow"))

    def test_concurrent_first_runs_migrate_once(self):
        root = self.legacy()
        command = PACKAGE / "bin/plovi"
        self.assertTrue(command.exists(), "canonical CLI must exist")
        runs = [subprocess.Popen([sys.executable, str(command), "inspect"], cwd=root,
                                env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                for _ in range(4)]
        outputs = [(p, p.communicate(timeout=40)) for p in runs]
        self.assertTrue(all(p.returncode == 0 for p, _ in outputs), str(outputs))
        self.assertEqual(sum(err.count("Moved .agentflow/ to .plovi/") for _, (_, err) in outputs), 1)

    def test_active_runner_blocks_migration(self):
        root = self.legacy()
        state = root / ".agentflow/local/evidence/task/state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({"status": "running"}))
        result = self.run_cli(root, "inspect")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((root / ".agentflow").exists())
        self.assertFalse((root / ".plovi").exists())

    def test_symlink_is_not_followed(self):
        root = self.repo("app")
        outside = self.root / "outside"; outside.mkdir()
        (outside / "keep").write_text("untouched")
        if os.name == "nt":
            (root / ".agentflow").write_text("not a directory")
        else:
            (root / ".agentflow").symlink_to(outside, target_is_directory=True)
        migration = self.migration()
        with self.assertRaisesRegex(Exception, "symlink|directory"):
            migration.migrate(root)
        self.assertEqual((outside / "keep").read_text(), "untouched")

    def test_preview_preserves_custom_profile_and_apply_uses_migration(self):
        root = self.legacy()
        profile_path = root / ".agentflow/project.json"
        profile = json.loads(profile_path.read_text())
        profile["tracking"]["provider"] = "linear"
        profile["git"]["worktree_directory"] = "custom-worktrees"
        profile_path.write_text(json.dumps(profile))
        setup = importlib.import_module(RUNTIME + ".setup")
        proposal = setup.propose(root)
        self.assertIn("migration", proposal)
        self.assertEqual(proposal["profile"]["tracking"]["provider"], "linear")
        self.assertEqual(proposal["profile"]["git"]["worktree_directory"], "custom-worktrees")
        self.assertFalse((root / ".plovi").exists())
        setup.apply(proposal, proposal["approval"])
        self.assertTrue((root / ".plovi/project.json").is_file())
        self.assertFalse((root / ".agentflow").exists())
        self.assertFalse(setup.propose(root)["changes"])

    def test_metadata_edits_after_interruption_are_not_overwritten(self):
        root = self.legacy()
        migration = self.migration()
        def fail(phase):
            if phase == "after-move":
                raise RuntimeError("interruption")
        with patch.object(migration, "checkpoint", side_effect=fail):
            with self.assertRaises(RuntimeError):
                migration.migrate(root)
        path = root / ".plovi/project.json"
        path.write_text(path.read_text() + "\n")
        before = path.read_bytes()
        with self.assertRaisesRegex(Exception, "changed externally"):
            migration.migrate(root)
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue((root / ".plovi-migration.json").is_file())

    def test_installed_runtime_receipt_rebases_and_uninstalls_owned_files(self):
        root = self.repo("app")
        install = importlib.import_module(RUNTIME + ".install")
        install.install(PACKAGE, project=root)
        self.setup_project(root)
        current = root / ".plovi"
        legacy = root / ".agentflow"
        current.rename(legacy)
        # Reproduce legacy path metadata without editing a versioned payload.
        for relative in ("project.json", "local/setup-baseline.json", "runtime/active.json", "runtime/receipt.json"):
            path = legacy / relative
            path.write_text(path.read_text().replace(".plovi", ".agentflow"))
        custom = legacy / "keep.bin"; custom.write_bytes(b"keep\0")
        migration = self.migration()
        migration.migrate(root)
        result = self.run_cli(root, "inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((current / "runtime/receipt.json").read_text())
        self.assertTrue(all(".agentflow" not in key for key in receipt["files"]))
        install.uninstall(project=root)
        self.assertFalse((current / "bin/plovi").exists())
        self.assertEqual((current / "keep.bin").read_bytes(), b"keep\0")

    def test_registered_children_and_worktrees_migrate_references(self):
        app = self.repo("workspace/app")
        checks = self.repo("workspace/checks")
        root = app.parent
        self.setup_project(root)
        for folder in (root, app, checks):
            current = folder / ".plovi"
            current.rename(folder / ".agentflow")
        for file in (root / ".agentflow/project.json", root / ".agentflow/local/setup-baseline.json"):
            file.write_text(file.read_text().replace(".plovi", ".agentflow"))
        self.git(app, "add", ".")
        self.git(app, "commit", "-m", "Legacy project reference")
        worktree = self.root / "task checkout"
        self.git(app, "worktree", "add", "-b", "task/rename", str(worktree))
        result = self.run_cli(worktree, "inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((root / ".plovi/project.json").exists())
        self.assertTrue((worktree / ".plovi/project-ref.json").exists())
        nested = checks / "nested"; nested.mkdir()
        result = self.run_cli(nested, "inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((checks / ".plovi/project-ref.json").exists())

    def test_legacy_managed_blocks_are_replaced_without_duplicates(self):
        setup = importlib.import_module(RUNTIME + ".setup")
        text = "Before\n<!-- agentflow:start -->\nold\n<!-- agentflow:end -->\nAfter"
        result = setup.managed(text, "new")
        self.assertEqual(result.count("<!-- plovi:start -->"), 1)
        self.assertNotIn("<!-- agentflow:", result)
        self.assertTrue(result.startswith("Before\n"))
        self.assertTrue(result.endswith("\nAfter"))

    def test_custom_files_snapshots_and_path_components_are_preserved(self):
        root = self.legacy()
        migration = self.migration()
        profile_path = root / ".agentflow/project.json"
        profile = json.loads(profile_path.read_text())
        profile["extensions"]["rules"] = "my.agentflow/rules"
        profile["custom"] = {"literal": ".agentflow"}
        profile_path.write_text(json.dumps(profile))
        snapshot = root / ".agentflow/local/evidence/done/snapshot.json"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_text('{"saved": ".agentflow/keep"}')
        migration.migrate(root)
        saved = json.loads((root / ".plovi/project.json").read_text())
        self.assertEqual(saved["extensions"]["rules"], "my.agentflow/rules")
        self.assertEqual(saved["custom"], {"literal": ".agentflow"})
        self.assertEqual((root / ".plovi/local/evidence/done/snapshot.json").read_text(), '{"saved": ".agentflow/keep"}')

    def test_setup_apply_migrates_child_references_before_discovery_updates(self):
        app = self.repo("workspace/app")
        checks = self.repo("workspace/checks")
        root = app.parent
        self.setup_project(root)
        for folder in (root, app, checks):
            (folder / ".plovi").rename(folder / ".agentflow")
        for file in (root / ".agentflow/project.json", root / ".agentflow/local/setup-baseline.json"):
            file.write_text(file.read_text().replace(".plovi", ".agentflow"))
        setup = importlib.import_module(RUNTIME + ".setup")
        proposal = setup.propose(root)
        self.assertFalse((app / ".plovi").exists())
        setup.apply(proposal, proposal["approval"])
        self.assertFalse((app / ".agentflow").exists(), "setup apply must move the existing child reference before writing its replacement")
        for child in (app, checks):
            self.assertTrue((child / ".plovi/project-ref.json").exists())
            result = self.run_cli(child, "inspect")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_moved_local_state_remains_git_ignored(self):
        root = self.legacy()
        ignore = root / ".gitignore"
        ignore.write_text(ignore.read_text().replace(".plovi", ".agentflow").replace("<!-- plovi:", "<!-- agentflow:") + "\n# Custom ignore\nmy-cache/\n")
        private = root / ".agentflow/local/private.json"
        private.write_text('{"fixture": "private local state"}')
        migration = self.migration()
        migration.migrate(root)
        result = subprocess.run(["git", "check-ignore", "-q", ".plovi/local/private.json"],
                                cwd=root, env=self.env)
        self.assertEqual(result.returncode, 0, "moving local state must not expose formerly ignored files")
        self.assertIn("# Custom ignore\nmy-cache/", ignore.read_text())
        self.assertEqual((root / ".plovi/local/private.json").read_text(), '{"fixture": "private local state"}')

    def test_install_preview_uses_legacy_receipt_without_mutation(self):
        root = self.repo("app")
        install = importlib.import_module(RUNTIME + ".install")
        util = importlib.import_module(RUNTIME + ".util")
        install.install(PACKAGE, project=root)
        self.setup_project(root)
        (root / ".plovi").rename(root / ".agentflow")
        for relative in ("project.json", "runtime/receipt.json", "runtime/active.json", "local/setup-baseline.json"):
            path = root / ".agentflow" / relative
            path.write_text(path.read_text().replace(".plovi", ".agentflow"))
        alias = root / ".agents/skills/af-review/scripts/dispatch.py"
        alias.write_text(alias.read_text() + "\n# Owned previous release\n")
        receipt_path = root / ".agentflow/runtime/receipt.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["files"][str(alias)]["sha256"] = util.file_hash(alias)
        receipt_path.write_text(json.dumps(receipt))
        before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        result = install.install(PACKAGE, project=root, dry_run=True)
        self.assertFalse(result["conflicts"], "preview must recognize ownership from the legacy receipt")
        self.assertIn("migration", result)
        self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})
