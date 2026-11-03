"""Portable command resolution, interactivity, absolute-path and path-equality checks."""
import os
import stat
import subprocess
import sys
import unittest
from tests.helpers import PACKAGE, WorkspaceTest, remove_tree
from plovi import process, util


class PlatformPathTests(WorkspaceTest):
    def test_absolute_anywhere(self):
        table = {"/x": True, "\\\\server\\share\\x": True, "C:\\x": True, "C:/x": True, "C:x": True,
                 "\\x": True, "x/y": False, "./x": False, "docs/**": False, "x\\y": False, "": False}
        for value, expected in table.items():
            with self.subTest(value=value):
                self.assertIs(util.is_absolute_anywhere(value), expected)

    @unittest.skipUnless(os.name == "nt", "Windows .cmd shims")
    def test_resolve_finds_cmd_shim(self):
        folder = self.root / "bin"
        folder.mkdir()
        (folder / "fixture-tool.cmd").write_text("@echo shim-ran\r\n")
        env = dict(self.env, PATH=str(folder) + os.pathsep + self.env["PATH"])
        argv = process.resolve(["fixture-tool", "--flag"], env)
        self.assertEqual(os.path.normcase(argv[0]), os.path.normcase(str(folder / "fixture-tool.cmd")))
        self.assertEqual(argv[1:], ["--flag"])
        result = util.run(["fixture-tool"], self.root, env=env)
        self.assertIn("shim-ran", result.stdout)

    @unittest.skipIf(os.name == "nt", "POSIX executable scripts")
    def test_resolve_finds_executable_script(self):
        folder = self.root / "bin"
        folder.mkdir()
        script = folder / "fixture-tool"
        script.write_text("#!/bin/sh\necho script-ran\n")
        script.chmod(0o755)
        env = dict(self.env, PATH=str(folder) + os.pathsep + self.env["PATH"])
        self.assertEqual(process.resolve(["fixture-tool"], env), [str(script)])
        self.assertIn("script-ran", util.run(["fixture-tool"], self.root, env=env).stdout)

    def test_resolve_keeps_paths_and_unknown_names(self):
        self.assertEqual(process.resolve(["./tool", 1]), ["./tool", "1"])
        self.assertEqual(process.resolve(["no-such-command-for-plovi-tests"], {"PATH": str(self.root)}),
                         ["no-such-command-for-plovi-tests"])
        self.assertIs(process.executable, process.resolve)

    def test_is_interactive_false_for_devnull(self):
        code = "import sys; sys.path.insert(0, sys.argv[1]); from plovi import util; print(util.is_interactive())"
        result = subprocess.run([sys.executable, "-c", code, str(PACKAGE / "runtime")], stdin=subprocess.DEVNULL,
                                env=self.env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "False", result.stderr)

    def test_is_interactive_false_for_closed_or_missing_stream(self):
        self.assertFalse(util.is_interactive(object()))
        with open(os.devnull) as stream:
            pass
        self.assertFalse(util.is_interactive(stream))

    def test_remove_tree_handles_read_only_files(self):
        tree = self.root / "tree/nested"
        tree.mkdir(parents=True)
        for name in ("a", "b"):
            (tree / name).write_text("locked")
            (tree / name).chmod(stat.S_IREAD)
        remove_tree(self.root / "tree")
        self.assertFalse((self.root / "tree").exists())

    def test_same_path_normalises_case_and_separators(self):
        folder = self.root / "Folder"
        folder.mkdir()
        self.assertTrue(util.same_path(folder, str(folder)))
        self.assertTrue(util.same_path(folder / "child" / "..", folder))
        self.assertFalse(util.same_path(folder, self.root))
        if os.name != "nt":
            link = self.root / "link"
            link.symlink_to(folder)
            self.assertTrue(util.same_path(link, folder))

    @unittest.skipUnless(os.name == "nt", "Windows paths compare without case and accept either separator")
    def test_same_path_windows_case_and_separators(self):
        folder = self.root / "Folder"
        folder.mkdir()
        self.assertTrue(util.same_path(str(folder).upper(), str(folder).lower()))
        self.assertTrue(util.same_path(str(folder).replace("\\", "/"), folder))
