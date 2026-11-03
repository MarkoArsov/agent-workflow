from __future__ import annotations
import io
import os
import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tests.helpers import PACKAGE, WorkspaceTest
from plovi import install, selfupdate
from plovi.util import WorkflowError, read_json, write_json


class SelfUpdateTests(WorkspaceTest):
    def source_copy(self):
        source = self.root / "source"
        for path in install.files_in(PACKAGE):
            target = source / path.relative_to(PACKAGE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        return source

    def linked(self):
        source = self.source_copy()
        install.install(source, link=True)
        running = patch("plovi.selfupdate.package_root", return_value=source)
        running.start(); self.addCleanup(running.stop)
        return source

    def refresh(self):
        stream = io.StringIO()
        selfupdate.maybe_refresh(stream)
        return stream.getvalue()

    def checkout(self):
        """A bare remote with one commit and a clone of it on main."""
        bare = self.bare_remote("origin")
        self.seed_remote(bare)
        clone = self.clone_repo(bare, "clone")
        return bare, clone

    def push_change(self, bare, name="later.txt"):
        other = self.clone_repo(bare, "other-" + name)
        (other / name).write_text("new\n")
        self.git(other, "add", ".")
        self.git(other, "commit", "-m", "Add " + name)
        self.git(other, "push", "origin", "main")

    def test_not_linked_is_a_no_op(self):
        self.assertEqual(self.refresh(), "")
        self.assertFalse(selfupdate.state_path().exists())

    def test_new_skill_refreshes_discovery_once(self):
        source = self.linked()
        self.refresh()
        skill = source / "skills/brand-new/SKILL.md"
        skill.parent.mkdir()
        skill.write_text("---\nname: brand-new\ndescription: Fixture skill for discovery.\n---\n")
        with patch("plovi.selfupdate._start_background"):
            note = self.refresh()
        self.assertIn("refreshed skill discovery", note)
        self.assertTrue((self.home / ".agents/skills/plovi-brand-new/SKILL.md").is_file())
        with patch("plovi.install.sync_linked") as sync, patch("plovi.selfupdate._start_background"):
            self.assertEqual(self.refresh(), "")
        sync.assert_not_called()

    def test_failed_sync_is_a_note_not_an_error(self):
        self.linked()
        with patch("plovi.install.sync_linked", side_effect=WorkflowError("conflicts")), \
                patch("plovi.selfupdate._start_background"):
            write_json(selfupdate.state_path(), {"discovery": "stale"})
            note = self.refresh()
        self.assertIn("could not refresh skill discovery", note)
        self.assertEqual(read_json(selfupdate.state_path())["discovery"], "stale")

    def test_background_check_is_throttled_and_can_be_turned_off(self):
        source = self.linked()
        (source / ".git").mkdir()
        with patch("plovi.selfupdate._start_background") as start:
            self.refresh(); self.refresh()
        self.assertEqual(start.call_count, 1)
        value = read_json(selfupdate.state_path())
        write_json(selfupdate.state_path(), value | {"last_fetch": time.time() - 7200, "follow": False})
        with patch("plovi.selfupdate._start_background") as start:
            self.refresh()
        start.assert_not_called()
        with patch.dict(os.environ, {"PLOVI_NO_SELF_UPDATE": "1"}), patch("plovi.selfupdate._start_background") as start:
            write_json(selfupdate.state_path(), value | {"last_fetch": 0, "follow": True})
            self.refresh()
        start.assert_not_called()

    def test_unexpected_errors_never_break_the_command(self):
        self.linked()
        with patch("plovi.selfupdate.refresh_discovery", side_effect=RuntimeError("boom")):
            self.assertIn("self-update skipped", self.refresh())

    def test_clean_checkout_fast_forwards(self):
        bare, clone = self.checkout()
        self.push_change(bare)
        result = selfupdate.update_checkout(clone, dict(selfupdate.DEFAULTS))
        self.assertEqual((result["status"], result["commits"]), ("updated", 1))
        self.assertTrue((clone / "later.txt").is_file())
        self.assertEqual(selfupdate.update_checkout(clone, dict(selfupdate.DEFAULTS))["status"], "current")

    def test_unsafe_checkouts_are_left_alone(self):
        bare, clone = self.checkout()
        self.push_change(bare)
        (clone / "README.md").write_text("edited\n")
        result = selfupdate.update_checkout(clone, dict(selfupdate.DEFAULTS))
        self.assertEqual(result["status"], "behind")
        self.assertIn("uncommitted", result["detail"])
        self.git(clone, "checkout", "--", "README.md")
        (clone / "mine.txt").write_text("mine\n")
        self.git(clone, "add", "."); self.git(clone, "commit", "-m", "Local work")
        result = selfupdate.update_checkout(clone, dict(selfupdate.DEFAULTS))
        self.assertIn("local commit", result["detail"])
        self.git(clone, "checkout", "-b", "feature")
        result = selfupdate.update_checkout(clone, dict(selfupdate.DEFAULTS))
        self.assertIn("on feature", result["detail"])
        self.assertFalse((clone / "later.txt").exists())

    def test_fetch_failure_is_reported(self):
        _, clone = self.checkout()
        self.git(clone, "remote", "set-url", "origin", str(self.root / "missing.git"))
        self.assertEqual(selfupdate.update_checkout(clone, dict(selfupdate.DEFAULTS))["status"], "fetch_failed")

    def test_background_result_is_shown_once(self):
        self.linked()
        write_json(selfupdate.state_path(), {"discovery": None, "last_fetch": time.time(), "shown": False,
                                              "last_result": {"status": "behind", "behind": 2, "branch": "main",
                                                              "detail": "It has uncommitted changes."}})
        with patch("plovi.selfupdate._start_background"):
            first, second = self.refresh(), self.refresh()
        self.assertIn("2 commit(s) behind main", first)
        self.assertNotIn("behind", second)

    def test_command_requires_a_linked_install(self):
        args = SimpleNamespace(follow=None, interval=None, background=False, now=False)
        with self.assertRaisesRegex(WorkflowError, "not a linked install"):
            selfupdate.command(args)

    def test_command_sets_follow_and_interval(self):
        self.linked()
        args = SimpleNamespace(follow="off", interval=30, background=False, now=False)
        result = selfupdate.command(args)
        self.assertEqual((result["follow"], result["interval_minutes"]), (False, 30))
        with self.assertRaisesRegex(WorkflowError, "5 minutes"):
            selfupdate.command(SimpleNamespace(follow=None, interval=1, background=False, now=False))

    def test_link_records_follow_choice_and_fingerprint(self):
        source = self.source_copy()
        with patch("sys.stdout", new_callable=io.StringIO):
            install.main(["--global", "--link", "--local-source", str(source), "--no-follow", "--agents", "codex"])
        value = read_json(selfupdate.state_path())
        self.assertFalse(value["follow"])
        self.assertEqual(value["discovery"], selfupdate.fingerprint(source))

    def test_cli_hook_skips_self_update_and_unattended_workers(self):
        from plovi import cli
        with patch("plovi.selfupdate.maybe_refresh") as hook, patch("plovi.cli.execute", return_value=None):
            cli.main(["self-update"])
            cli.main(["worktrees"])
        self.assertEqual(hook.call_count, 1)
