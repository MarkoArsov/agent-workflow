"""Read-only repository and workflow detection with cited observations."""
from __future__ import annotations
import json
import os
import re
import shutil
import tomllib
from pathlib import Path
from .profile import defaults
from .util import WorkflowError, common_dir, git, run

SKIP = {".git", ".agent-workflow", ".venv", "venv", "node_modules", "vendor", "dist", "build", "__pycache__", ".local", "ai-plans", "worktrees"}

def repositories(root: Path) -> list[Path]:
    if (root / ".git").exists():
        return [root]
    found, commons = [], set()
    for current, directories, _ in os.walk(root):
        here = Path(current)
        directories[:] = sorted(d for d in directories if d not in SKIP and not d.startswith("."))
        if len(here.relative_to(root).parts) > 3:
            directories[:] = []; continue
        if (here / ".git").exists():
            common = common_dir(here)
            if common and common not in commons and (here / ".git").is_dir():
                found.append(here); commons.add(common)
            directories[:] = []
    return found

def scan(root: Path) -> dict:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise WorkflowError("Setup needs an existing project directory")
    if not (root / ".git").exists():
        top = run(["git", "rev-parse", "--show-toplevel"], root, check=False)
        if top.returncode == 0:
            root = Path(top.stdout.strip()).resolve()
    roots = repositories(root)
    if not roots:
        raise WorkflowError("No Git repositories found; supply a repository or its parent folder")
    findings, repos = [], []
    def record(repo, subject, value, source, confidence="detected"):
        findings.append({"repository": repo, "subject": subject, "value": value, "source": source, "confidence": confidence})
    used = set()
    for repo in roots:
        name = re.sub(r"[^a-z0-9._-]+", "-", repo.name.lower()).strip("-") or "app"
        if name in used:
            name += "-" + str(len(used) + 1)
        used.add(name)
        rel = repo.relative_to(root).as_posix()
        commands, languages = {}, []
        def command(key, argv, parser="generic", source="", confidence="detected"):
            value = {"argv": argv, "cwd": ".", "parser": parser, "timeout_seconds": 300}
            if parser == "generic":
                value["success_pattern"] = r"(?s).+"
            commands[key] = value
            record(name, "command." + key, value, source, confidence)
        pkg = repo / "package.json"
        if pkg.is_file():
            try:
                data = json.loads(pkg.read_text())
            except ValueError as exc:
                raise WorkflowError(f"Invalid package.json in {rel}: {exc}") from exc
            manager = "pnpm" if (repo / "pnpm-lock.yaml").exists() else "yarn" if (repo / "yarn.lock").exists() else "npm"
            languages.append("node")
            for key in ("build", "test", "lint", "format", "typecheck"):
                if key in data.get("scripts", {}):
                    script = data["scripts"][key]
                    parser = "jest" if "jest" in script or "vitest" in script else "playwright" if "playwright" in script else "generic"
                    command(key, [manager, "run", key], parser, rel + "/package.json")
        py = repo / "pyproject.toml"
        if py.is_file() or (repo / "requirements.txt").is_file() or list(repo.glob("*.py")):
            languages.append("python")
            data = tomllib.loads(py.read_text()) if py.is_file() else {}
            tools = data.get("tool", {})
            if "pytest" in tools or (repo / "pytest.ini").exists():
                command("test", ["python3", "-m", "pytest"], "pytest", rel + "/pyproject.toml")
            elif (repo / "tests").is_dir():
                command("test", ["python3", "-m", "unittest", "discover", "-s", "tests"], "unittest", rel + "/tests", "suggested")
            if "ruff" in tools:
                command("lint", ["python3", "-m", "ruff", "check", "."], source=rel + "/pyproject.toml")
        solutions = sorted([*repo.glob("*.sln"), *repo.glob("*.slnx"), *repo.glob("*.csproj")])
        if solutions:
            languages.append("dotnet")
            target = solutions[0].name
            command("build", ["dotnet", "build", target], source=rel + "/" + target)
            command("test", ["dotnet", "test", target], "dotnet", rel + "/" + target)
        if (repo / "go.mod").is_file():
            languages.append("go")
            command("build", ["go", "build", "./..."], source=rel + "/go.mod")
            command("test", ["go", "test", "-v", "./..."], "go", rel + "/go.mod")
        if (repo / "Cargo.toml").is_file():
            languages.append("rust")
            command("build", ["cargo", "build"], source=rel + "/Cargo.toml")
            command("test", ["cargo", "test"], "rust", rel + "/Cargo.toml")
        make = repo / "Makefile"
        if make.is_file():
            for key in ("build", "test", "lint", "format"):
                if key not in commands and re.search(r"^" + key + r"\s*:", make.read_text(), re.M):
                    command(key, ["make", key], source=rel + "/Makefile")
        task = next(iter(repo.glob("Taskfile.y*ml")), None)
        if task:
            for key in ("build", "test", "lint", "format"):
                if key not in commands and re.search(r"^\s{2}" + key + r":", task.read_text(), re.M):
                    command(key, ["task", key], source=rel + "/" + task.name)
        symbolic = git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", check=False)
        branches = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
        base = symbolic.removeprefix("refs/remotes/origin/") if symbolic else next((x for x in ("main", "master") if x in branches), git(repo, "branch", "--show-current", check=False) or "main")
        record(name, "base_branch", base, rel + "/.git", "detected" if symbolic else "suggested")
        recent = git(repo, "log", "-8", "--format=%s", check=False).splitlines()
        style = "conventional" if recent and sum(bool(re.match(r"^(feat|fix|docs|chore|test|refactor)(\(.+\))?!?:", x)) for x in recent) > len(recent) / 2 else "imperative"
        record(name, "commit_style", style, "recent Git subjects", "suggested")
        role = "e2e" if re.search(r"(e2e|checks|acceptance)", repo.name, re.I) else "infra" if any(repo.glob("*.tf")) else "docs" if (repo / "mkdocs.yml").exists() else "application"
        record(name, "roles", [role], rel, "suggested")
        record(name, "languages", languages, rel)
        record(name, "checkout_strategy", "worktree" if len(git(repo, "worktree", "list", "--porcelain").split("worktree ")) > 2 else "current-checkout", "git worktree list", "suggested")
        ci = sorted(p.name for p in (repo / ".github/workflows").glob("*") if p.is_file())
        if ci:
            record(name, "ci", "github-actions", rel + "/.github/workflows")
        bots = []
        if any((repo / f).exists() for f in (".coderabbit.yaml", ".coderabbit.yml")):
            bots.append("coderabbit")
        if (repo / ".cursor/BUGBOT.md").exists():
            bots.append("bugbot")
        if bots:
            record(name, "review_bots", bots, rel)
        instructions = [f for f in ("AGENTS.md", "CLAUDE.md", "README.md") if (repo / f).is_file()]
        record(name, "instructions", instructions, rel)
        repos.append({"id": name, "path": rel, "roles": [role], "languages": languages, "base_branch": base, "remote": "origin", "task_policy": "when-changed", "checkout_strategy": "current-checkout", "commands": commands})
    profile = defaults(root, repos)
    styles = [f["value"] for f in findings if f["subject"] == "commit_style"]
    if styles and all(s == "conventional" for s in styles):
        profile["git"]["commit_style"] = "conventional"
    return {"root": str(root), "profile": profile, "findings": findings,
            "available_agents": [p for p, binary in (("codex", "codex"), ("claude", "claude"), ("cursor", "agent")) if shutil.which(binary)],
            "questions": ["Confirm repository roles and task/checkout policies.", "Confirm commands, delivery, tracker, and plan storage.", "Choose agents, exact model routes, and trusted or restricted permissions."]}
