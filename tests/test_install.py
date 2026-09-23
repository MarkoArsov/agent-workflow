from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from unittest.mock import patch
from tests.helpers import PACKAGE, WorkspaceTest
from agent_workflow import install
from agent_workflow.extensions import copy_skill
from agent_workflow.util import WorkflowError, read_json, write_json

class InstallTests(WorkspaceTest):
    def clean_env(self):
        return {k: v for k, v in self.env.items() if k != "AGENT_WORKFLOW_PACKAGE"}

    def source_version(self, version):
        source = self.root / ("source-" + version)
        for path in install.files_in(PACKAGE):
            target = source / path.relative_to(PACKAGE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        write_json(source / "workflow-package.json", {"name": "agent-workflow", "schema_version": 1, "version": version})
        (source / "runtime/agent_workflow/__init__.py").write_text('__version__ = "' + version + '"\n')
        return source

    def invoke(self, path, cwd, *args):
        return subprocess.run([sys.executable, str(path), *args], cwd=cwd, env=self.clean_env(), capture_output=True, text=True, check=True).stdout

    def test_global_install_discovery_reinstall_and_owned_uninstall(self):
        root = self.repo("project")
        foreign = self.home / ".agents/skills/unrelated/SKILL.md"
        foreign.parent.mkdir(parents=True); foreign.write_text("user content")
        result = install.install(PACKAGE)
        self.assertEqual(result["version"], "0.1.0")
        shim = self.home / ".local/bin/agent-workflow"
        self.assertEqual(self.invoke(shim, root, "--version").strip(), "0.1.0")
        wrapper = self.home / ".agents/skills/aw-project-setup/scripts/dispatch.py"
        resolved = self.invoke(wrapper, root).strip()
        self.assertIn("/versions/0.1.0/skills/project-setup/SKILL.md", resolved)
        install.install(PACKAGE)
        modified = self.home / ".agents/skills/aw-review/SKILL.md"
        modified.write_text("user-modified adapter")
        removed = install.uninstall()
        self.assertIn(str(modified), removed["preserve_modified"])
        self.assertEqual(modified.read_text(), "user-modified adapter")
        self.assertEqual(foreign.read_text(), "user content")
        self.assertFalse(shim.exists())

    def test_project_install_before_setup_and_compatible_global_fallback(self):
        root = self.repo("project")
        install.install(PACKAGE, project=root)
        wrapper = root / ".agents/skills/aw-project-setup/scripts/dispatch.py"
        self.assertIn(str(root / ".agent-workflow/runtime"), self.invoke(wrapper, root))
        project = self.setup_project(root)
        self.assertIn(str(root / ".agent-workflow/runtime"), self.invoke(wrapper, root))
        install.install(PACKAGE)
        global_wrapper = self.home / ".agents/skills/aw-review/scripts/dispatch.py"
        self.assertIn(str(root / ".agent-workflow/runtime"), self.invoke(global_wrapper, root))
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
        self.assertEqual(self.invoke(project.config / "bin/agent-workflow", root, "--version").strip(), "0.1.1")
        self.assertTrue((project.config / "runtime/versions/0.1.0").exists())

    def test_non_git_parent_and_relocated_native_payload(self):
        app = self.repo("workspace/app"); checks = self.repo("workspace/checks")
        parent = app.parent
        install.install(PACKAGE, project=parent)
        for child in (app, checks):
            output = self.invoke(child / ".claude/skills/aw-project-setup/scripts/dispatch.py", child)
            self.assertIn(str(parent / ".agent-workflow/runtime"), output)
        project = self.setup_project(parent)
        relocated = self.source_version("0.1.0")
        install.uninstall(project=parent)
        result = self.invoke(relocated / "skills/review/scripts/resolve.py", checks)
        self.assertIn(str(relocated / "skills/review/SKILL.md"), result)

    def test_collision_and_failed_update_roll_back(self):
        root = self.repo("project")
        install.install(PACKAGE, project=root)
        source = self.source_version("0.1.1")
        receipt = root / ".agent-workflow/runtime/receipt.json"
        old = receipt.read_bytes()
        real_write = install.atomic_write
        def fail(path, *args, **kwargs):
            if path.name == "agent-workflow":
                raise OSError("simulated write failure")
            return real_write(path, *args, **kwargs)
        with patch("agent_workflow.install.atomic_write", side_effect=fail):
            with self.assertRaisesRegex(OSError, "simulated"):
                install.install(source, project=root)
        self.assertEqual(receipt.read_bytes(), old)
        self.assertFalse((root / ".agent-workflow/runtime/versions/0.1.1").exists())
        wrapper = root / ".agents/skills/aw-review/SKILL.md"
        wrapper.write_text("Unowned user edit")
        with self.assertRaisesRegex(WorkflowError, "conflicts"):
            install.install(source, project=root)
        self.assertEqual(wrapper.read_text(), "Unowned user edit")

    def test_local_shell_bootstrap_only_uses_isolated_home(self):
        root = self.repo("project")
        result = subprocess.run(["sh", str(PACKAGE / "install.sh"), "--local-source", str(PACKAGE), "--project", str(root)],
                                cwd=root, env=self.clean_env(), text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)["mode"], "project")
        self.assertFalse((self.home / ".local/bin/agent-workflow").exists())

