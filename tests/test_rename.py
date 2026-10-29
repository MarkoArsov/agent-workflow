"""Public-name contracts; legacy names here exercise supported aliases."""
from __future__ import annotations
import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from tests.helpers import PACKAGE, WorkspaceTest

RUNTIME = "plovi" if (PACKAGE / "runtime/plovi").exists() else "agentflow"
install = importlib.import_module(RUNTIME + ".install")

class RenameTests(WorkspaceTest):
    def invoke(self, path, cwd, *args):
        env = {k: v for k, v in self.env.items() if k not in {"PLOVI_PACKAGE", "AGENTFLOW_PACKAGE"}}
        return subprocess.run([sys.executable, str(path), *args], cwd=cwd, env=env,
                              capture_output=True, text=True)

    def test_fresh_install_has_plovi_and_legacy_launcher(self):
        root = self.repo("app")
        install.install(PACKAGE)
        canonical = self.home / ".local/bin/plovi"
        self.assertTrue(canonical.is_file(), "fresh installs must expose plovi")
        result = self.invoke(canonical, root, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: plovi", result.stdout)
        self.assertEqual(result.stderr, "")
        alias = self.invoke(self.home / ".local/bin/agentflow", root, "--help")
        self.assertEqual(alias.stdout, result.stdout)
        self.assertEqual(alias.returncode, result.returncode)
        self.assertEqual(alias.stderr.count("agentflow is now plovi"), 1)

    def test_alias_preserves_output_arguments_and_exit_status(self):
        root = self.repo("app")
        install.install(PACKAGE)
        canonical = self.home / ".local/bin/plovi"
        self.assertTrue(canonical.is_file(), "canonical launcher must be installed")
        for args in (("--version",), ("unknown-command",)):
            normal = self.invoke(canonical, root, *args)
            old = self.invoke(self.home / ".local/bin/agentflow", root, *args)
            self.assertEqual((old.returncode, old.stdout), (normal.returncode, normal.stdout))
            self.assertEqual(old.stderr.splitlines()[1:], normal.stderr.splitlines())
            self.assertIn("this alias works until 1.0", old.stderr.splitlines()[0])

    def test_all_host_skill_aliases_resolve_same_override(self):
        root = self.repo("app")
        project = self.setup_project(root)
        extensions = importlib.import_module(RUNTIME + ".extensions")
        override = extensions.copy_skill(project, "review")
        install.install(PACKAGE, agents=["claude", "codex", "cursor"])
        for location in (self.home / ".agents/skills", self.home / "claude/skills"):
            canonical = location / "plovi-review/scripts/dispatch.py"
            self.assertTrue(canonical.is_file(), "all hosts need prefixed skills")
            result = self.invoke(canonical, root)
            old = self.invoke(location / "af-review/scripts/dispatch.py", root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(override))
            self.assertEqual(old.stdout, result.stdout)
            self.assertEqual(old.returncode, 0, old.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(old.stderr.count("af-review is now plovi-review"), 1)

    def test_native_plugin_prefixed_entries_and_aliases(self):
        plugin = json.loads((PACKAGE / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(plugin["name"], "plovi")
        for name in ("plovi-review", "af-review"):
            wrapper = PACKAGE / "templates/plugin-skills" / name / "SKILL.md"
            self.assertTrue(wrapper.is_file(), name)
            self.assertIn("name: " + name, wrapper.read_text())

    def test_discovery_alias_collisions_preserve_user_files(self):
        root = self.repo("app")
        for name in ("plovi-review", "af-review"):
            foreign = self.home / ".agents/skills" / name / "SKILL.md"
            foreign.parent.mkdir(parents=True, exist_ok=True)
            foreign.write_text("User-owned content")
            with self.assertRaisesRegex(Exception, "conflicts"):
                install.install(PACKAGE)
            self.assertEqual(foreign.read_text(), "User-owned content")
            foreign.unlink()
        self.assertFalse((self.home / ".local/bin/plovi").exists())

    def test_audit_rejects_old_names_in_docs_and_hidden_configuration(self):
        script = PACKAGE / "scripts/check_rename.py"
        self.assertTrue(script.is_file(), "rename audit must exist")
        for relative in ("docs/guide.md", ".plovi/settings.json"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Use Agent Flow for this project.\n")
            result = subprocess.run([sys.executable, str(script), str(self.root)],
                                    env=self.env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(relative, result.stdout + result.stderr)
            target.unlink()

    def test_native_wrappers_execute_common_dispatcher(self):
        root = self.repo("app")
        self.setup_project(root)
        expected = str(PACKAGE / "skills/review/SKILL.md")
        for name in ("plovi-review", "af-review"):
            result = self.invoke(PACKAGE / "templates/plugin-skills" / name / "scripts/dispatch.py", root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), expected)
            self.assertEqual("is now" in result.stderr, name.startswith("af-"))

    def test_older_global_and_project_pins_select_legacy_module(self):
        root = self.repo("app")
        project = self.setup_project(root)
        legacy = project.config / "runtime/versions/0.0.9"
        module = legacy / "runtime/agentflow"
        module.mkdir(parents=True)
        (legacy / "workflow-package.json").write_text(json.dumps({"name": "agentflow", "version": "0.0.9", "schema_version": 1}))
        (module / "__init__.py").write_text("")
        (module / "cli.py").write_text('def main(args):\n    print("legacy-pinned-runtime")\n    return 0\n')
        profile_file = project.config / "project.json"
        profile = json.loads(profile_file.read_text())
        profile["package"]["version"] = "0.0.9"
        profile_file.write_text(json.dumps(profile))
        install.install(PACKAGE)
        result = self.invoke(self.home / ".local/bin/plovi", root, "--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "legacy-pinned-runtime")
        # The same pin remains selectable through a project-only installation.
        from importlib import import_module
        adapters = import_module(RUNTIME + ".adapters")
        launcher = project.config / "bin/plovi"
        launcher.parent.mkdir(parents=True)
        launcher.write_text(adapters.adapter_source("launch.py").replace("LOCAL_RUNTIME = None", "LOCAL_RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'"))
        result = self.invoke(launcher, root, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "legacy-pinned-runtime")

    def test_project_reinstall_accepts_unchanged_setup_owned_aliases(self):
        root = self.repo("app")
        self.setup_project(root)
        alias = root / ".agents/skills/af-review/scripts/dispatch.py"
        baseline_path = root / ".plovi/local/setup-baseline.json"
        baseline = json.loads(baseline_path.read_text())
        previous = alias.read_text() + "\n# Previous release adapter\n"
        alias.write_text(previous)
        baseline["files"][alias.relative_to(root).as_posix()] = previous
        baseline_path.write_text(json.dumps(baseline))
        preview = install.install(PACKAGE, project=root, dry_run=True)
        self.assertFalse(preview["conflicts"], "unchanged setup-owned adapters are replaceable")
        result = install.install(PACKAGE, project=root)
        self.assertFalse(result["conflicts"])
        self.assertNotIn("Previous release adapter", alias.read_text())
