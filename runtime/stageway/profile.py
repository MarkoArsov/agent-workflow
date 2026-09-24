"""Validate the supported profile format without a runtime dependency."""
from __future__ import annotations
from pathlib import Path
from .util import WorkflowError, contained, identifier

PROVIDERS = {"codex", "claude", "cursor"}
BASE_STAGES = ["implement-tests", "implement", "review", "commit-and-push", "draft-pr"]

def validate_command(command: dict):
    if not isinstance(command, dict):
        raise WorkflowError("Commands must be objects")
    argv = command.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise WorkflowError("Each command requires a nonempty argv string array")
    timeout = command.get("timeout_seconds", 300)
    if not isinstance(timeout, int) or not 1 <= timeout <= 86400:
        raise WorkflowError("Command timeout must be between 1 and 86400 seconds")
    cwd = command.get("cwd", ".")
    if not isinstance(cwd, str) or Path(cwd).is_absolute() or ".." in Path(cwd).parts:
        raise WorkflowError("Command cwd must stay inside its repository")
    if Path(argv[0]).name in {"sh", "bash", "zsh", "cmd", "powershell", "pwsh"} and not command.get("shell", False):
        raise WorkflowError("Shell commands require shell: true")
    for key in command.get("env", {}):
        if any(word in key.lower() for word in ("secret", "token", "password", "key")):
            raise WorkflowError("Use env_refs for credentials, not literal command environment values")
    if not all(isinstance(x, str) for x in command.get("env_refs", [])):
        raise WorkflowError("env_refs must name environment variables")

def validate(profile: dict, root: Path | None = None) -> dict:
    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        raise WorkflowError("Expected project schema_version 1")
    project = profile.get("project", {})
    identifier(project.get("id", ""))
    if project.get("kind") not in {"single-repo", "multi-repo"}:
        raise WorkflowError("Project kind must be single-repo or multi-repo")
    repos = profile.get("repositories")
    if not isinstance(repos, list) or not repos:
        raise WorkflowError("Register at least one repository")
    ids, paths = set(), set()
    for repo in repos:
        name = identifier(repo.get("id", ""))
        path = repo.get("path")
        if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
            raise WorkflowError(f"{name}: repository path must be relative to the project")
        if name in ids or path in paths:
            raise WorkflowError("Repository IDs and paths must be unique")
        ids.add(name); paths.add(path)
        if root:
            contained(root, path)
        if repo.get("task_policy") not in {"always", "when-changed", "never"}:
            raise WorkflowError(f"{name}: invalid task_policy")
        if repo.get("checkout_strategy") not in {"current-checkout", "feature-branch", "worktree"}:
            raise WorkflowError(f"{name}: invalid checkout_strategy")
        if not repo.get("base_branch") or not repo.get("remote"):
            raise WorkflowError(f"{name}: base_branch and remote are required")
        for command in repo.get("commands", {}).values():
            validate_command(command)
    if set(profile.get("agents", [])) - PROVIDERS:
        raise WorkflowError("Unsupported agent in profile")
    if profile.get("execution", {}).get("permission_mode") not in {"trusted", "restricted"}:
        raise WorkflowError("Choose trusted or restricted execution")
    if profile.get("tracking", {}).get("provider") not in {"none", "github", "linear", "notion", "custom"}:
        raise WorkflowError("Unsupported tracker; use custom with a connector")
    for key in ("directory", "evidence_directory"):
        value = profile.get("planning", {}).get(key)
        if not isinstance(value, str) or Path(value).is_absolute() or ".." in Path(value).parts:
            raise WorkflowError(f"planning.{key} must be relative")
        if root:
            contained(root, value)
    for name, value in profile.get("extensions", {}).items():
        if not isinstance(value, str) or Path(value).is_absolute() or ".." in Path(value).parts:
            raise WorkflowError(f"extensions.{name} must be relative")
        if root:
            contained(root, value)
    return profile

def defaults(root: Path, repositories: list[dict]) -> dict:
    import re
    from . import __version__
    name = re.sub(r"[^a-z0-9._-]+", "-", root.name.lower()).strip("-") or "project"
    return {
        "schema_version": 1,
        "project": {"id": name, "kind": "single-repo" if len(repositories) == 1 and repositories[0]["path"] == "." else "multi-repo", "configuration_root": "."},
        "package": {"version": __version__},
        "agents": ["claude", "codex", "cursor"],
        "repositories": repositories,
        "planning": {"directory": "ai-plans", "evidence_directory": ".stageway/local/evidence"},
        "git": {"branch_template": "feature/{task}", "commit_style": "imperative", "worktree_directory": ".stageway/local/worktrees"},
        "delivery": {"pull_requests": "draft", "publish": "plan-selected", "merge_to_base": "explicit"},
        "tracking": {"provider": "none"},
        "execution": {"permission_mode": "trusted", "provider_settings": {}},
        "pipeline": {"enabled": True, "default_stages": BASE_STAGES, "routes": {}},
        "extensions": {name: ".stageway/" + name for name in ("skills", "rules", "references", "connectors")} | {"stages": ".stageway/stages.json"}
    }

