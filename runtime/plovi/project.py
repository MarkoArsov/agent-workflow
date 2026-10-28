"""Explicit project membership, including sibling repos and Git worktrees."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .profile import validate
from .util import WorkflowError, common_dir, contained, read_json, user_data, run, write_json
from .migration import configuration, migrate as migrate_project, CURRENT, LEGACY

def marker(path):
    try:
        return read_json(path)
    except WorkflowError:
        if path.exists():
            raise
        return None


@dataclass
class Project:
    root: Path
    profile: dict
    configuration_path: Path | None = None

    @property
    def config(self):
        return self.configuration_path or self.root / CURRENT

    def repository(self, name: str) -> dict:
        for repo in self.profile["repositories"]:
            if repo["id"] == name:
                return repo
        raise WorkflowError(f"Repository is not registered: {name}")

    def repo_path(self, name: str) -> Path:
        return contained(self.root, self.repository(name)["path"])

    def accepts(self, start: Path) -> bool:
        if start == self.root:
            return True
        active_common = common_dir(start)
        for repo in self.profile["repositories"]:
            path = self.repo_path(repo["id"])
            if active_common and path.exists() and active_common == common_dir(path):
                return True
            if not active_common and start.is_relative_to(path):
                return True
        return False

def load(root: Path, *, migrate=True) -> Project:
    root = root.expanduser().resolve()
    config = configuration(root)
    data = marker(config / "project.json")
    if data is None:
        config = configuration(root)
        data = marker(config / "project.json")
    if data is None:
        raise WorkflowError(f"No project profile at {root}; run project-setup")
    validate(data, root)
    if migrate:
        migrate_project(root)
        config = root / CURRENT
        data = marker(config / "project.json")
    if data is None:
        config = configuration(root)
        data = marker(config / "project.json")
    return Project(root, validate(data, root), config)

def resolve(start: Path | str = ".", explicit: Path | str | None = None, *, migrate=True) -> Project:
    start = Path(start).expanduser().resolve()
    if start.is_file():
        start = start.parent
    def accept(root, reference=None):
        project = load(root, migrate=False)
        if not project.accepts(start):
            return None
        if migrate:
            project = load(root)
            references = [reference] if reference and reference != root else []
            if is_worktree:
                top = run(["git", "rev-parse", "--show-toplevel"], start, check=False)
                if top.returncode == 0:
                    active = Path(top.stdout.strip()).resolve()
                    if (active / LEGACY / "project-ref.json").is_file():
                        references.append(active)
            for selected in dict.fromkeys(references):
                if (selected / LEGACY).exists():
                    migrate_project(selected)
                ref_path = selected / CURRENT / "project-ref.json"
                if ref_path.is_file():
                    import os
                    ref = read_json(ref_path)
                    updated = ref | {"root": os.path.relpath(project.root, selected)}
                    if updated != ref:
                        write_json(ref_path, updated)
        return project
    common = common_dir(start)
    metadata = run(["git", "rev-parse", "--git-dir"], start, check=False)
    is_worktree = bool(common and metadata.returncode == 0 and (start / metadata.stdout.strip()).resolve() != common)
    if explicit:
        project = accept(Path(explicit))
        if project is None:
            raise WorkflowError("The active repository does not belong to the requested project")
        return project
    search = [start, *start.parents]
    if common:
        original = common.parent
        search += [original, *original.parents]
    for candidate in dict.fromkeys(search):
        # Read the marker before checking for migration conflicts, so unrelated
        # ancestor projects cannot be mutated by discovery.
        for name in (CURRENT, LEGACY, CURRENT):
            ref = marker(candidate / name / "project-ref.json")
            target = (candidate / ref["root"]).resolve() if ref else candidate
            raw = next((data for folder in (CURRENT, LEGACY, CURRENT)
                        if (data := marker(target / folder / "project.json")) is not None), None)
            if raw is None:
                continue
            probe = Project(target, validate(raw, target))
            if not probe.accepts(start):
                if ref and not is_worktree:
                    raise WorkflowError("Project reference does not include the active repository")
                continue
            return accept(target, candidate if ref else None)
    if common:
        matches = []
        for entry in read_json(user_data() / "projects.json", []):
            if str(common) in entry.get("common_dirs", []) and Path(entry["root"]).exists():
                project = load(Path(entry["root"]), migrate=False)
                if project.accepts(start):
                    matches.append(project)
        if len(matches) == 1:
            return accept(matches[0].root)
        if len(matches) > 1:
            raise WorkflowError("Multiple registered projects match; pass --project")
    raise WorkflowError("No project profile matches this location; run project-setup")
