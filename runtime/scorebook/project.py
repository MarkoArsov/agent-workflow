"""Explicit project membership, including sibling repos and Git worktrees."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .profile import validate
from .util import WorkflowError, common_dir, contained, read_json, user_data, run

@dataclass
class Project:
    root: Path
    profile: dict

    @property
    def config(self):
        return self.root / ".scorebook"

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

def load(root: Path) -> Project:
    root = root.expanduser().resolve()
    path = root / ".scorebook/project.json"
    data = read_json(path)
    if data is None:
        raise WorkflowError(f"No project profile at {root}; run project-setup")
    return Project(root, validate(data, root))

def resolve(start: Path | str = ".", explicit: Path | str | None = None) -> Project:
    start = Path(start).expanduser().resolve()
    if start.is_file():
        start = start.parent
    if explicit:
        project = load(Path(explicit))
        if not project.accepts(start):
            raise WorkflowError("The active repository does not belong to the requested project")
        return project
    common = common_dir(start)
    metadata = run(["git", "rev-parse", "--git-dir"], start, check=False)
    is_worktree = bool(common and metadata.returncode == 0 and (start / metadata.stdout.strip()).resolve() != common)
    for candidate in [start, *start.parents]:
        ref = read_json(candidate / ".scorebook/project-ref.json")
        if ref:
            target = (candidate / ref["root"]).resolve()
            if is_worktree and not (target / ".scorebook/project.json").is_file():
                continue
            project = load(target)
            if not project.accepts(start):
                if is_worktree:
                    continue
                raise WorkflowError("Project reference does not include the active repository")
            return project
        if (candidate / ".scorebook/project.json").is_file():
            project = load(candidate)
            if project.accepts(start):
                return project
    common = common_dir(start)
    if common:
        original = common.parent
        for candidate in [original, *original.parents]:
            ref = read_json(candidate / ".scorebook/project-ref.json")
            target = (candidate / ref["root"]).resolve() if ref else candidate
            if (target / ".scorebook/project.json").is_file():
                project = load(target)
                if project.accepts(start):
                    return project
        registry = read_json(user_data() / "projects.json", [])
        matches = []
        for entry in registry:
            if str(common) in entry.get("common_dirs", []) and Path(entry["root"]).exists():
                project = load(Path(entry["root"]))
                if project.accepts(start):
                    matches.append(project)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise WorkflowError("Multiple registered projects match; pass --project")
    raise WorkflowError("No project profile matches this location; run project-setup")
