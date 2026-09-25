from tests.helpers import WorkspaceTest, PACKAGE
from scorebook.extensions import copy_skill, new_skill, resolve_skill, snapshot
from scorebook.setup import propose, apply

class ExtensionTests(WorkspaceTest):
    def test_override_and_new_skill_are_project_local_and_discoverable(self):
        a = self.setup_project(self.repo("alpha"))
        b = self.setup_project(self.repo("beta"))
        override = copy_skill(a, "project-setup")
        override.write_text(override.read_text() + "\nA project-specific instruction.\n")
        new = new_skill(a, "release-notes", "Draft release notes for this project.")
        self.assertEqual(resolve_skill("project-setup", a), override)
        self.assertEqual(resolve_skill("project-setup", b), PACKAGE / "skills/project-setup/SKILL.md")
        self.assertEqual(resolve_skill("release-notes", a), new)
        proposal = propose(a.root)
        apply(proposal, proposal["approval"])
        self.assertTrue((a.root / ".agents/skills/sb-release-notes/SKILL.md").is_file())
        self.assertIn("A project-specific instruction.", snapshot(a)["skills"]["project-setup"]["content"])
        self.assertNotIn("release-notes", snapshot(b)["skills"])

