"""The user-level projects registry: add, list, remove and setup registration.

Text layout fixed by test_text_format: one line per entry in registration order,
"<id>  <root>", with "  missing" appended when the root no longer exists.
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from tests.helpers import WorkspaceTest
from tests.fixtures.control_plane import TIMESTAMP, ControlPlaneMixin, rows
from plovi.project import load
from plovi.util import read_json, user_data


class ProjectRegistryTests(ControlPlaneMixin, WorkspaceTest):
    def registry(self):
        return read_json(user_data() / "projects.json", [])

    def run_cli(self, *args):
        return self.cli(*args, cwd=self.root, check=False)

    def listing(self):
        response = self.ok(self.run_cli("projects", "list"))
        return rows(json.loads(response.stdout), "projects")

    def configured(self, name):
        root = self.repo(name)
        self.setup_project(root)
        return load(root)

    def test_add_list_remove_keeps_files(self):
        project = self.configured("one")
        identifier = project.profile["project"]["id"]
        added = self.run_cli("projects", "add", project.root)
        self.assertEqual(added.returncode, 0, added.stdout + added.stderr)
        entries = [e for e in self.registry() if e["id"] == identifier]
        self.assertEqual(len(entries), 1)
        self.assertEqual(set(entries[0]), {"id", "root", "added_at"})
        self.assertEqual(Path(entries[0]["root"]).resolve(), project.root.resolve())
        self.assertRegex(entries[0]["added_at"], TIMESTAMP.pattern)
        listed = [row for row in self.listing() if row["id"] == identifier]
        self.assertEqual(len(listed), 1)
        self.assertIs(listed[0]["exists"], True)
        before = sorted(p.relative_to(project.root).as_posix() for p in project.root.rglob("*") if ".git" not in p.parts)
        self.ok(self.run_cli("projects", "remove", identifier))
        self.assertEqual([e for e in self.registry() if e["id"] == identifier], [])
        self.assertEqual([row for row in self.listing() if row["id"] == identifier], [])
        after = sorted(p.relative_to(project.root).as_posix() for p in project.root.rglob("*") if ".git" not in p.parts)
        self.assertEqual(before, after, "remove never deletes files on disk")
        self.assertTrue((project.root / ".plovi/project.json").is_file())
        events = [e for e in self.ledger_events(project) if e["subject"] == {"kind": "project", "id": identifier}]
        types = [e["type"] for e in events]
        self.assertIn("project.registered", types)
        self.assertEqual(types[-1], "project.unregistered")
        registered = [e for e in events if e["type"] == "project.registered"][-1]
        self.assertEqual(Path(registered["data"]["root"]).resolve(), project.root.resolve())

    def test_setup_registers_project(self):
        root = self.repo("fresh")
        answers = self.root / "answers.json"; answers.write_text(json.dumps({"confirmed_defaults": True}))
        proposal = self.root / "proposal.json"
        preview = json.loads(self.ok(self.run_cli("setup", root, "--answers", answers, "--output", proposal)).stdout)
        self.assertEqual(self.registry(), [], "a preview registers nothing")
        self.ok(self.run_cli("setup", "--apply", proposal, "--approve", preview["approval"]))
        identifier = load(root).profile["project"]["id"]
        self.assertEqual([(e["id"], Path(e["root"]).resolve()) for e in self.registry()], [(identifier, root.resolve())])
        self.assertIn(identifier, [row["id"] for row in self.listing()])
        events = [e["type"] for e in self.ledger_events(load(root))
                  if e["subject"] == {"kind": "project", "id": identifier}]
        self.assertIn("project.registered", events)

    def test_add_is_idempotent_and_rejects_conflicting_root(self):
        project = self.configured("one")
        identifier = project.profile["project"]["id"]
        for _ in range(2):
            self.ok(self.run_cli("projects", "add", project.root))
        self.assertEqual(len([e for e in self.registry() if e["id"] == identifier]), 1)
        copy = self.repo("copy")
        (copy / ".plovi").mkdir()
        shutil.copy(project.root / ".plovi/project.json", copy / ".plovi/project.json")
        self.assertEqual(load(copy, migrate=False).profile["project"]["id"], identifier, "fixture shares the project ID")
        before = self.registry()
        refused = self.run_cli("projects", "add", copy)
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("projects remove", refused.stderr, "the error names the fix")
        self.assertEqual(self.registry(), before)

    def test_text_format(self):
        first = self.configured("one")
        second = self.configured("two")
        for project in (first, second):
            self.ok(self.run_cli("projects", "add", project.root))
        shutil.rmtree(second.root)
        text = self.ok(self.run_cli("projects", "list", "--format", "text")).stdout
        expected = [f"{e['id']}  {e['root']}" + ("" if Path(e["root"]).exists() else "  missing") for e in self.registry()]
        self.assertEqual(text.splitlines(), expected)
        self.assertIn(f"{second.profile['project']['id']}  {second.root}  missing", expected)
        self.assertIn(f"{first.profile['project']['id']}  {first.root}", expected)
