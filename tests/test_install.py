from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from tests.helpers import PACKAGE, WorkspaceTest
from agentflow import install
from agentflow.extensions import copy_skill, new_skill
from agentflow.util import WorkflowError, read_json, write_json

class InstallTests(WorkspaceTest):
    def test_pre_rename_link_keeps_receipt_settings_and_discovery(self):
        caller = self.repo("project")
        install.install(PACKAGE, link=True)
        current = self.home / "data/agentflow"
        legacy = current.with_name("agent-workflow")
        write_json(current / "models/settings.json", {"schema_version": 1, "providers": ["codex"]})
        current.rename(legacy)
        receipt = read_json(legacy / "receipt.json")
        write_json(legacy / "receipt.json", receipt | {"source_sha256": "before-rename"})
        self.assertEqual(install.installation_root(), legacy)
        install.sync_linked()
        self.assertFalse(current.exists())
        self.assertEqual(read_json(legacy / "models/settings.json")["providers"], ["codex"])
        self.assertEqual(self.invoke(self.home / ".local/bin/agentflow", caller, "--version").strip(), "0.1.0")
        resolved = self.invoke(self.home / ".agents/skills/af-publish-workflow/scripts/dispatch.py", caller).strip()
        self.assertEqual(resolved, str(PACKAGE / "skills/publish-workflow/SKILL.md"))

    def test_publish_workflow_resolves_without_project_setup_or_mutating_caller(self):
        caller = self.repo("unconfigured application")
        before = self.git(caller, "rev-parse", "HEAD")
        for linked in (False, True):
            with self.subTest(linked=linked):
                install.install(PACKAGE, link=linked)
                wrapper = self.home / ".agents/skills/af-publish-workflow/scripts/dispatch.py"
                resolved = self.invoke(wrapper, caller).strip()
                expected = PACKAGE if linked else self.home / "data/agentflow/versions/0.1.0"
                self.assertEqual(resolved, str(expected / "skills/publish-workflow/SKILL.md"))
                native = self.invoke(expected / "skills/publish-workflow/scripts/resolve.py", caller).strip()
                self.assertEqual(native, resolved)
                self.assertEqual(self.git(caller, "rev-parse", "HEAD"), before)
                self.assertEqual(self.git(caller, "status", "--porcelain"), "")
                self.assertFalse((caller / ".agentflow").exists())
                # The global exception must not bypass setup for ordinary project skills.
                ordinary = subprocess.run(
                    [sys.executable, str(self.home / ".agents/skills/af-review/scripts/dispatch.py")],
                    cwd=caller, env=self.clean_env(), capture_output=True, text=True)
                self.assertNotEqual(ordinary.returncode, 0)
                install.uninstall()

    def clean_env(self):
        return {k: v for k, v in self.env.items() if k != "AGENTFLOW_PACKAGE"}

    def bootstrap(self, *args, cwd):
        """Run the platform's one-line installer from this checkout."""
        if os.name == "nt":
            command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PACKAGE / "install.ps1")]
            env = {**self.clean_env(), "AGENTFLOW_NO_MODIFY_PATH": "1"}
        else:
            command, env = ["sh", str(PACKAGE / "install.sh")], self.clean_env()
        return subprocess.run([*command, "--local-source", str(PACKAGE), *map(str, args)],
                              cwd=cwd, env=env, text=True, capture_output=True, check=True)

    def source_version(self, version):
        source = self.root / ("source-" + version)
        for path in install.files_in(PACKAGE):
            target = source / path.relative_to(PACKAGE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        write_json(source / "workflow-package.json", read_json(PACKAGE / "workflow-package.json") | {"version": version})
        (source / "runtime/agentflow/__init__.py").write_text('__version__ = "' + version + '"\n')
        return source

    def invoke(self, path, cwd, *args):
        return subprocess.run([sys.executable, str(path), *args], cwd=cwd, env=self.clean_env(), capture_output=True, text=True, check=True).stdout

    def test_global_install_discovery_reinstall_and_owned_uninstall(self):
        root = self.repo("project")
        foreign = self.home / ".agents/skills/unrelated/SKILL.md"
        foreign.parent.mkdir(parents=True); foreign.write_text("user content")
        result = install.install(PACKAGE)
        self.assertEqual(result["version"], "0.1.0")
        shim = self.home / ".local/bin/agentflow"
        self.assertEqual(self.invoke(shim, root, "--version").strip(), "0.1.0")
        wrapper = self.home / ".agents/skills/af-setup/scripts/dispatch.py"
        resolved = self.invoke(wrapper, root).strip()
        self.assertIn("/versions/0.1.0/skills/setup/SKILL.md", Path(resolved).as_posix())
        install.install(PACKAGE)
        modified = self.home / ".agents/skills/af-review/SKILL.md"
        modified.write_text("user-modified adapter")
        removed = install.uninstall()
        self.assertIn(str(modified), removed["preserve_modified"])
        self.assertEqual(modified.read_text(), "user-modified adapter")
        self.assertEqual(foreign.read_text(), "user content")
        self.assertFalse(shim.exists())

    def test_project_install_before_setup_and_compatible_global_fallback(self):
        root = self.repo("project")
        install.install(PACKAGE, project=root)
        wrapper = root / ".agents/skills/af-setup/scripts/dispatch.py"
        self.assertIn(str(root / ".agentflow/runtime"), self.invoke(wrapper, root))
        project = self.setup_project(root)
        self.assertIn(str(root / ".agentflow/runtime"), self.invoke(wrapper, root))
        install.install(PACKAGE)
        global_wrapper = self.home / ".agents/skills/af-review/scripts/dispatch.py"
        self.assertIn(str(root / ".agentflow/runtime"), self.invoke(global_wrapper, root))
        custom = copy_skill(project, "review")
        with custom.open("a") as output:
            output.write("\nPROJECT CUSTOMIZATION\n")
        install.uninstall(project=root)
        self.assertIn(str(custom), self.invoke(global_wrapper, root))
        self.assertTrue(project.config.joinpath("project.json").exists())

    def test_update_pins_new_version_preserves_extensions_and_reports_upstream(self):
        root = self.repo("project")
        install.install(PACKAGE, project=root)
        project = self.setup_project(root)
        custom = copy_skill(project, "review")
        with custom.open("a") as output:
            output.write("\nCUSTOM\n")
        old = custom.read_bytes()
        source = self.source_version("0.1.1")
        with (source / "skills/review/SKILL.md").open("a") as output:
            output.write("\nNew upstream guidance.\n")
        result = install.install(source, project=root)
        self.assertEqual(read_json(project.config / "project.json")["package"]["version"], "0.1.1")
        self.assertEqual(old, custom.read_bytes())
        self.assertEqual(result["override_updates"][0]["skill"], "review")
        self.assertEqual(self.invoke(project.config / "bin/agentflow", root, "--version").strip(), "0.1.1")
        self.assertTrue((project.config / "runtime/versions/0.1.0").exists())

    def test_non_git_parent_and_relocated_native_payload(self):
        app = self.repo("workspace/app"); checks = self.repo("workspace/checks")
        parent = app.parent
        install.install(PACKAGE, project=parent)
        for child in (app, checks):
            output = self.invoke(child / ".claude/skills/af-setup/scripts/dispatch.py", child)
            self.assertIn(str(parent / ".agentflow/runtime"), output)
        project = self.setup_project(parent)
        relocated = self.source_version("0.1.0")
        install.uninstall(project=parent)
        result = self.invoke(relocated / "skills/review/scripts/resolve.py", checks)
        self.assertIn(str(relocated / "skills/review/SKILL.md"), result)

    def test_collision_and_failed_update_roll_back(self):
        root = self.repo("project")
        install.install(PACKAGE, project=root)
        source = self.source_version("0.1.1")
        receipt = root / ".agentflow/runtime/receipt.json"
        old = receipt.read_bytes()
        real_write = install.atomic_write
        def fail(path, *args, **kwargs):
            if path.name == "agentflow":
                raise OSError("simulated write failure")
            return real_write(path, *args, **kwargs)
        with patch("agentflow.install.atomic_write", side_effect=fail):
            with self.assertRaisesRegex(OSError, "simulated"):
                install.install(source, project=root)
        self.assertEqual(receipt.read_bytes(), old)
        self.assertFalse((root / ".agentflow/runtime/versions/0.1.1").exists())
        wrapper = root / ".agents/skills/af-review/SKILL.md"
        wrapper.write_text("Unowned user edit")
        with self.assertRaisesRegex(WorkflowError, "conflicts"):
            install.install(source, project=root)
        self.assertEqual(wrapper.read_text(), "Unowned user edit")

    def test_local_shell_bootstrap_only_uses_isolated_home(self):
        root = self.repo("project")
        result = self.bootstrap("--project", root, "--json", cwd=root)
        self.assertEqual(json.loads(result.stdout)["mode"], "project")
        self.assertFalse((self.home / ".local/bin/agentflow").exists())

    def test_linked_checkout_live_code_and_skills_follow_updates_without_copying(self):
        root = self.repo("project")
        source = self.source_version("0.1.0")
        install.install(source, link=True)
        project = self.setup_project(root)
        shim = self.home / ".local/bin/agentflow"
        wrapper = self.home / ".agents/skills/af-review/scripts/dispatch.py"
        self.assertEqual(self.invoke(wrapper, root).strip(), str(source / "skills/review/SKILL.md"))
        (source / "runtime/agentflow/__init__.py").write_text('__version__ = "0.1.1"\n')
        marker = read_json(source / "workflow-package.json")
        write_json(source / "workflow-package.json", marker | {"version": "0.1.1"})
        self.assertEqual(self.invoke(shim, root, "--version").strip(), "0.1.1")
        custom = copy_skill(project, "review")
        self.assertEqual(self.invoke(wrapper, root).strip(), str(custom))
        install.sync_linked()
        self.assertEqual(install.sync_linked()["status"], "unchanged")
        self.assertFalse((install.installation_root() / "versions").exists())
        install.uninstall()
        self.assertTrue((source / "runtime/agentflow/cli.py").is_file())
        self.assertTrue(custom.is_file())

    def test_link_sync_renames_adds_removes_and_preserves_unowned_entries(self):
        source = self.source_version("0.1.0")
        install.install(source, link=True)
        foreign = self.home / ".agents/skills/unrelated/SKILL.md"
        foreign.parent.mkdir(); foreign.write_text("keep me")
        new = source / "skills/new-task/SKILL.md"
        new.parent.mkdir(); new.write_text("---\nname: new-task\ndescription: Test new discovery.\n---\n")
        shutil.rmtree(source / "skills/review")
        marker = read_json(source / "workflow-package.json")
        marker["discovery"] = {"prefix": "next", "aliases": {"project-setup": "start"}}
        write_json(source / "workflow-package.json", marker)
        preview = install.sync_linked(dry_run=True)
        self.assertFalse(preview["conflicts"])
        self.assertTrue((self.home / ".agents/skills/af-setup").exists())
        install.sync_linked()
        self.assertFalse((self.home / ".agents/skills/af-setup").exists())
        self.assertFalse((self.home / ".agents/skills/next-review").exists())
        self.assertTrue((self.home / ".agents/skills/next-new-task/SKILL.md").is_file())
        self.assertTrue((self.home / ".agents/skills/next-start/SKILL.md").is_file())
        self.assertEqual(foreign.read_text(), "keep me")
        install.uninstall()
        self.assertFalse((self.home / ".agents/skills/next-start").exists())

    def test_link_sync_conflicts_rollback_and_shared_host_directory(self):
        source = self.source_version("0.1.0")
        claude = self.home / "claude/skills"
        claude.mkdir(parents=True)
        shared = self.home / ".agents/skills"
        shared.parent.mkdir(); shared.symlink_to(claude, target_is_directory=True)
        result = install.install(source, link=True)
        self.assertEqual(len(result["files"]), 3 * len(install.catalog(package=source)) + (2 if os.name == "nt" else 1))
        receipt = install.installation_root() / "receipt.json"
        before = receipt.read_bytes()
        original = (claude / "af-review/SKILL.md").read_text()
        (claude / "af-review/SKILL.md").write_text("keep modified adapter")
        with self.assertRaisesRegex(WorkflowError, "conflicts"):
            install.sync_linked()
        self.assertEqual(receipt.read_bytes(), before)
        (claude / "af-review/SKILL.md").write_text(original)
        marker = read_json(source / "workflow-package.json")
        marker["discovery"]["prefix"] = "renamed"
        write_json(source / "workflow-package.json", marker)
        real_write = install.atomic_write
        def fail(path, *args, **kwargs):
            if path.parent.name == "renamed-review":
                raise OSError("simulated rename failure")
            return real_write(path, *args, **kwargs)
        with patch("agentflow.install.atomic_write", side_effect=fail):
            with self.assertRaisesRegex(OSError, "simulated"):
                install.sync_linked()
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual((claude / "af-review/SKILL.md").read_text(), original)
        self.assertFalse((claude / "renamed-setup/SKILL.md").exists())

    def test_project_pin_precedes_link_and_incompatible_link_is_rejected(self):
        root = self.repo("project")
        source = self.source_version("0.1.1")
        install.install(source, link=True)
        install.install(PACKAGE, project=root)
        setup_wrapper = self.home / ".agents/skills/af-setup/scripts/dispatch.py"
        self.assertIn("runtime/versions/0.1.0", self.invoke(setup_wrapper, root).replace("\\", "/"))
        self.assertEqual(self.invoke(self.home / ".local/bin/agentflow", root, "--version").strip(), "0.1.0")
        self.setup_project(root)
        wrapper = self.home / ".agents/skills/af-review/scripts/dispatch.py"
        self.assertIn("runtime/versions/0.1.0", self.invoke(wrapper, root).replace("\\", "/"))
        install.uninstall(project=root)
        self.assertIn(str(source), self.invoke(wrapper, root))
        marker = read_json(source / "workflow-package.json")
        write_json(source / "workflow-package.json", marker | {"schema_version": 2})
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke(wrapper, root)
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke(self.home / ".local/bin/agentflow", root, "--version")

    def test_linked_setup_uses_global_discovery_and_keeps_project_extensions(self):
        root = self.repo("project")
        install.install(PACKAGE, link=True)
        project = self.setup_project(root)
        self.assertFalse((root / ".agents/skills/af-review/SKILL.md").exists())
        custom = copy_skill(project, "review")
        wrapper = self.home / ".agents/skills/af-review/scripts/dispatch.py"
        self.assertEqual(self.invoke(wrapper, root).strip(), str(custom))
        local_skill = new_skill(project, "local-task", "Project-only task")
        self.setup_project(root)
        local = root / ".agents/skills/af-local-task/scripts/dispatch.py"
        self.assertEqual(str(local_skill), self.invoke(local, root).strip())
        self.assertFalse((root / ".agents/skills/af-review/SKILL.md").exists())


    def test_plain_installer_detects_agents_and_explains_next_steps(self):
        found = {"codex": "/usr/bin/codex"}
        with patch("agentflow.install.shutil.which", side_effect=lambda name: found.get(name)):
            self.assertEqual(install.detect_agents(), ["codex"])
        with patch("agentflow.install.shutil.which", return_value=None):
            self.assertEqual(install.detect_agents(), ["claude", "codex", "cursor"])
        result = self.bootstrap("--agents", "codex", cwd=self.root)
        self.assertIn("installed (global)", result.stdout)
        self.assertIn("af-* for Codex", result.stdout)
        self.assertIn('codex "Use the af-setup skill"', result.stdout)
        self.assertNotIn("claude \"/af-setup\"", result.stdout)
        self.assertIn("to your PATH", result.stdout)
        self.assertTrue((self.home / ".local/bin/agentflow").exists())
        self.assertFalse((self.home / "claude/skills").exists())
