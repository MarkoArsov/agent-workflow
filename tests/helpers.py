from __future__ import annotations
import atexit
import contextlib
import functools
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "runtime"))


@functools.lru_cache(maxsize=None)
def windows_launcher(script, python=None):
    """An .exe that runs script with this Python, or None without pip's launchers.

    A .cmd shim goes through cmd.exe, which splits arguments at & and newlines.
    pip builds its console scripts the same way: its distlib launcher, a shebang
    line, then a zip whose __main__.py runs the script.
    """
    import importlib.util
    import platform
    import struct
    import zipfile
    spec = importlib.util.find_spec("pip")
    if spec is None or not spec.submodule_search_locations:
        return None
    name = "t32.exe" if struct.calcsize("P") == 4 else "t64-arm.exe" if platform.machine().upper() == "ARM64" else "t64.exe"
    launcher = Path(list(spec.submodule_search_locations)[0]) / "_vendor/distlib" / name
    if not launcher.exists():
        return None
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("__main__.py", f"import runpy\nrunpy.run_path({str(script)!r}, run_name='__main__')\n")
    shebang = f'#!"{python or sys.executable}"\n'.encode()
    return launcher.read_bytes() + shebang + archive.getvalue()


def install_script(folder, name, script):
    """Put a Python script on folder as the command name; return its path.

    Windows gets an .exe from windows_launcher, or a .cmd shim without pip.
    """
    folder.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        target = folder / name
        shutil.copy(script, target)
        target.chmod(0o755)
        return target
    launcher = windows_launcher(str(script))
    if launcher:
        target = folder / f"{name}.exe"
        target.write_bytes(launcher)
    else:
        target = folder / f"{name}.cmd"
        target.write_text(f'@"{sys.executable}" "{script}" %*\r\n')
    return target


def remove_tree(path):
    """Remove a tree that may hold read-only files, such as Git objects on Windows."""
    def retry(function, failed, _info):
        os.chmod(failed, stat.S_IWRITE)
        function(failed)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)


def wait_for(predicate, timeout=10, interval=0.05):
    """Poll until predicate() is truthy and return its value; fail after timeout seconds."""
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() >= deadline:
            raise AssertionError(f"Condition not met within {timeout} s")
        time.sleep(interval)


_CACHE = {}


def _cache_root():
    """Per-process scratch space for fixture templates, removed when the process exits."""
    if "root" not in _CACHE:
        _CACHE["root"] = Path(tempfile.mkdtemp(prefix="plovi-fixture-cache-")).resolve()
        atexit.register(remove_tree, _CACHE["root"])
    return _CACHE["root"]


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.home), "XDG_DATA_HOME": str(self.home / "data"),
                    "XDG_CONFIG_HOME": str(self.home / "config"), "XDG_CACHE_HOME": str(self.home / "cache"),
                    "CODEX_HOME": str(self.home / "codex"), "CLAUDE_CONFIG_DIR": str(self.home / "claude"),
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    # Background maintenance adds and removes .git files while tests compare trees.
                    "GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "maintenance.auto", "GIT_CONFIG_VALUE_0": "false",
                    "GIT_CONFIG_KEY_1": "gc.auto", "GIT_CONFIG_VALUE_1": "0",
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                    "PYTHONDONTWRITEBYTECODE": "1", "PLOVI_PACKAGE": str(PACKAGE),
                    # UTC0 means UTC to both POSIX and the Windows C runtime, which requires an offset.
                    "TZ": "UTC0"}
        if os.name == "nt":
            # Path.home() reads USERPROFILE; child processes need the system variables.
            self.env["USERPROFILE"] = str(self.home)
            self.env["APPDATA"] = str(self.home / "roaming")
            self.env["LOCALAPPDATA"] = str(self.home / "local")
            self.env.update({key: os.environ[key] for key in ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC",
                                                              "PATHEXT", "TEMP", "TMP") if key in os.environ})
            self.env["PYTHONUTF8"] = "1"
        else:
            self.env["LC_ALL"] = "C.UTF-8"
        self.patch = unittest.mock.patch.dict(os.environ, self.env, clear=True)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def git(self, root, *args, check=True):
        return subprocess.run(["git", "-C", str(root), *args], env=self.env, text=True, capture_output=True, check=check).stdout.strip()

    def repo(self, name):
        """A plain repository on main with README.md "# Fixture" in one commit, copied from a per-process template."""
        path = self.root / name
        if path.exists() and any(path.iterdir()):
            self.git(path, "init", "-b", "main")
            (path / "README.md").write_text("# Fixture\n")
            self.git(path, "add", ".")
            self.git(path, "commit", "-m", "Initialize fixture")
            return path
        if "repo" not in _CACHE:
            template = _cache_root() / "repo"
            template.mkdir()
            self.git(template, "init", "-b", "main")
            (template / "README.md").write_text("# Fixture\n")
            self.git(template, "add", ".")
            self.git(template, "commit", "-m", "Initialize fixture")
            _CACHE["repo"] = template
        # Templates are plain repositories: worktree metadata would hold absolute paths.
        shutil.copytree(_CACHE["repo"], path, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.sample"))
        return path

    def bare_remote(self, name):
        path = self.root / f"remotes/{name}.git"
        path.mkdir(parents=True, exist_ok=True)
        self.git(path, "init", "--bare", "-b", "main")
        return path

    def seed_remote(self, bare, filename="README.md", content="# Fixture\n"):
        """Push one "Initialize" commit holding only filename to main, built in a cached per-process repository."""
        seeder = _CACHE.get("seeder")
        if seeder is None:
            seeder = _cache_root() / "seeder"
            seeder.mkdir()
            self.git(seeder, "init", "-b", "main")
            _CACHE["seeder"] = seeder
        key = ("tree", filename, content)
        if key not in _CACHE:
            # Match the bytes write_text() produced in a checkout, including Windows line endings.
            data = content.replace("\n", os.linesep).encode()
            blob = subprocess.run(["git", "-C", str(seeder), "hash-object", "-w", "--stdin"], input=data, env=self.env,
                                  capture_output=True, check=True).stdout.decode().strip()
            tree = subprocess.run(["git", "-C", str(seeder), "mktree"], input=f"100644 blob {blob}\t{filename}\n".encode(),
                                  env=self.env, capture_output=True, check=True).stdout.decode().strip()
            _CACHE[key] = tree
        commit = self.git(seeder, "commit-tree", _CACHE[key], "-m", "Initialize")
        self.git(seeder, "push", "--quiet", str(bare), f"{commit}:refs/heads/main")

    def clone_repo(self, bare, name):
        path = self.root / name
        subprocess.run(["git", "clone", str(bare), str(path)], env=self.env, check=True, capture_output=True, text=True)
        return path

    def install_github_fake(self, state=None):
        """Install tests/fixtures/github_fake.py as gh, first on PATH; return its state file.

        The fake knows only what the state scripts; it logs calls to <state>.calls.json.
        """
        binary = self.root / "bin"
        install_script(binary, "gh", PACKAGE / "tests/fixtures/github_fake.py")
        path = self.root / "github-state.json"
        path.write_text(json.dumps(state or {}, indent=1), encoding="utf-8")
        for environment in (self.env, os.environ):
            if str(binary) not in environment["PATH"].split(os.pathsep):
                environment["PATH"] = str(binary) + os.pathsep + environment["PATH"]
            environment["PLOVI_TEST_GITHUB_STATE"] = str(path)
        return path

    def setup_project(self, path, patch=None):
        from plovi.setup import apply, propose
        p = propose(path, {"confirmed_defaults": True, "profile": patch or {}})
        apply(p, p["approval"])
        from plovi.project import load
        return load(path)

    def cli(self, *args, cwd=None, check=True):
        return subprocess.run([sys.executable, str(PACKAGE / "bin/plovi"), *map(str, args)],
                              cwd=cwd or PACKAGE, env=self.env, stdin=subprocess.DEVNULL,
                              text=True, capture_output=True, check=check)

    def cli_inproc(self, *args, cwd=None, check=True):
        """Run plovi.cli.main in this process like cli(): same environment, no stdin, captured output."""
        from plovi import cli, operations
        argv = [str(item) for item in args]
        stdout, stderr = io.StringIO(), io.StringIO()
        saved = (dict(os.environ), os.getcwd(), sys.argv, sys.stdin, operations.FORWARDED, operations.WORKER)
        try:
            os.environ.clear()
            os.environ.update(self.env)
            os.chdir(cwd or PACKAGE)
            sys.argv = [str(PACKAGE / "bin/plovi"), *argv]
            sys.stdin = io.StringIO("")
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    code = cli.main(argv)
                except SystemExit as exc:
                    if isinstance(exc.code, str):
                        print(exc.code, file=sys.stderr)
                    code = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
        finally:
            os.environ.clear()
            os.environ.update(saved[0])
            os.chdir(saved[1])
            sys.argv, sys.stdin, operations.FORWARDED, operations.WORKER = saved[2:]
        result = subprocess.CompletedProcess(["plovi", *argv], code, stdout.getvalue(), stderr.getvalue())
        if check and code:
            raise subprocess.CalledProcessError(code, result.args, result.stdout, result.stderr)
        return result

import unittest.mock


class InProcessCli:
    """Run CLI commands in this process, except those that cross the process boundary.

    Commands that launch, forward to or watch other processes (main() dispatches them to a
    pinned runtime, which prints from its own process) stay subprocesses, as do
    the tests named in SUBPROCESS_TESTS: they keep each command's process contract tested.
    """
    PROCESS_COMMANDS = frozenset({"run", "pipeline", "watch", "verify", "migrate", "status"})
    SUBPROCESS_TESTS = frozenset()

    def cli(self, *args, cwd=None, check=True):
        words = [str(item) for item in args]
        command, skip = None, False
        for word in words:
            if skip:
                skip = False
            elif word == "--project":
                skip = True
            elif not word.startswith("-"):
                command = word
                break
        if (self._testMethodName in self.SUBPROCESS_TESTS or command in self.PROCESS_COMMANDS
                or "--help" in words or "-h" in words):
            return super().cli(*args, cwd=cwd, check=check)
        return self.cli_inproc(*args, cwd=cwd, check=check)


class HardeningTest(WorkspaceTest):
    """Reuse the runner fixture without inheriting its test methods."""

    def fixture(self, steps, *, stages=None):
        from tests.test_runner import RunnerTests
        return RunnerTests.fixture(self, steps, stages=stages or ["implement"])

    def calls(self):
        path = self.scenario.with_suffix(".calls.json")
        return json.loads(path.read_text()) if path.exists() else []

    def save_plan(self):
        from plovi.util import write_json
        write_json(self.manifest_path, {k: v for k, v in self.plan.items() if not k.startswith("_")})

    def task_cli(self, *args, check=False):
        return self.cli("--project", self.project.root, *args, check=check)

    def install_gh_double(self):
        binary = self.root / "bin"
        install_script(binary, "gh", PACKAGE / "tests/fixtures/gh_double.py")
        path = self.root / "gh-state.json"
        self.env["PLOVI_TEST_GH_STATE"] = str(path)
        os.environ["PLOVI_TEST_GH_STATE"] = str(path)
        return path
