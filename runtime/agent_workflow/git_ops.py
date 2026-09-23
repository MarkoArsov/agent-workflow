"""Repository participation, outcome guards, and resumable delivery mechanics."""
from __future__ import annotations
import os
from pathlib import Path
from .manifest import matches
from .util import WorkflowError, contained, digest, git, json_text, run

def files(root):
    result = run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], root).stdout
    entries = {}
    for name in sorted(set(result.split("\0")) - {""}):
        path = root / name
        if path.is_symlink():
            entries[name] = {"sha256": digest(os.readlink(path)), "mode": "symlink"}
        elif path.is_file():
            entries[name] = {"sha256": digest(path.read_bytes()), "mode": path.stat().st_mode & 0o111}
    return entries

def snapshot(project, checkouts=None):
    checkouts = checkouts or {}
    result = {}
    for repo in project.profile["repositories"]:
        root = Path(checkouts.get(repo["id"], project.repo_path(repo["id"])))
        result[repo["id"]] = {"head": git(root, "rev-parse", "HEAD"), "branch": git(root, "branch", "--show-current"),
                              "index": digest(git(root, "ls-files", "--stage", "-z")),
                              "files": files(root)}
        parked = project.repo_path(repo["id"])
        if root.resolve() != parked.resolve():
            result[repo["id"] + ":parked"] = {"head": git(parked, "rev-parse", "HEAD"),
                                               "index": digest(git(parked, "ls-files", "--stage", "-z")),
                                               "branch": git(parked, "branch", "--show-current"), "files": files(parked)}
    return result

def fingerprint(value):
    return digest(json_text({k: v["files"] for k, v in value.items()}))

def changes(before, after):
    return {repo: sorted(name for name in set(before[repo]["files"]) | set(after[repo]["files"])
                         if before[repo]["files"].get(name) != after[repo]["files"].get(name))
            for repo in before}

def guard(before, after, manifest, stage, *, allow_commits=False, custom=None):
    selected = {r["id"]: r for r in manifest["repositories"]}
    failures = []
    changed = changes(before, after)
    for name, paths in changed.items():
        row = selected.get(name, {})
        patterns = row.get("test_paths", []) if stage == "implement-tests" else row.get("paths", [])
        if custom is not None:
            patterns = [p["path"] for p in custom.get("outputs", []) if p["repository"] == name]
        if not allow_commits and (before[name]["head"], before[name]["branch"]) != (after[name]["head"], after[name]["branch"]):
            failures.append(f"{name}: stage changed Git HEAD or branch")
        if not allow_commits and before[name].get("index") != after[name].get("index"):
            failures.append(f"{name}: stage changed the Git index")
        for path in paths:
            if row.get("access") != "write" or not matches(path, patterns):
                failures.append(f"{name}/{path}: outside stage write contract")
    if failures:
        raise WorkflowError("Scope violation; changes retained for inspection:\n" + "\n".join(failures))
    return changed

def prepare(project, manifest):
    result = {}
    for row in manifest["repositories"]:
        name = row["id"]; repo = project.repository(name); root = project.repo_path(name)
        if row["access"] == "read":
            result[name] = str(root); continue
        strategy = repo["checkout_strategy"]
        branch = row.get("branch")
        if strategy != "current-checkout":
            if not branch or branch == repo["base_branch"]:
                raise WorkflowError(f"{name}: branch strategy requires an explicit feature branch")
            git(root, "check-ref-format", "--branch", branch)
            if git(root, "status", "--porcelain"):
                raise WorkflowError(f"{name}: commit/stash existing changes before preparing a new checkout")
            exists = bool(git(root, "branch", "--list", branch))
            if strategy == "feature-branch":
                git(root, "switch", *([branch] if exists else ["-c", branch, repo["base_branch"]]))
            else:
                directory = contained(project.root, project.profile["git"]["worktree_directory"])
                target = directory / manifest["task"] / name
                if target.exists():
                    if git(target, "branch", "--show-current") != branch:
                        raise WorkflowError(f"Existing worktree has a different branch: {target}")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    git(root, "worktree", "add", *([str(target), branch] if exists else ["-b", branch, str(target), repo["base_branch"]]))
                root = target
        if branch and git(root, "branch", "--show-current") != branch:
            raise WorkflowError(f"{name}: active branch differs from the approved task branch")
        if git(root, "diff", "--cached", "--name-only"):
            raise WorkflowError(f"{name}: existing staged changes must be committed or unstaged first")
        result[name] = str(root)
    return result

def dirty_paths(root):
    output = run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], root).stdout
    # Rename records have a second path; pre-existing changes are never task-owned.
    result = set()
    pieces = output.split("\0")
    for piece in pieces:
        if piece:
            result.add(piece[3:] if len(piece) > 3 and piece[2] == " " else piece)
    return sorted(result)

def deliver(project, manifest, state, save, *, pull_requests=False):
    from .integrations.github import draft_pr
    baseline = state["baseline"]
    current = snapshot(project, state["checkouts"])
    paths = changes(baseline, current)
    for row in manifest["repositories"]:
        if row["access"] != "write":
            continue
        name = row["id"]; repo = project.repository(name); root = Path(state["checkouts"][name])
        progress = state.setdefault("delivery", {}).setdefault(name, {})
        branch = git(root, "branch", "--show-current")
        if branch != row.get("branch") or branch == repo["base_branch"] or not branch:
            raise WorkflowError(f"{name}: refusing delivery from an unexpected or base branch")
        if not progress.get("commit"):
            changed = paths[name]
            if not changed:
                progress["unchanged"] = True; save(); continue
            overlap = set(changed) & set(state["initial_dirty"].get(name, []))
            if overlap:
                raise WorkflowError(f"{name}: refusing to commit pre-existing user changes: {sorted(overlap)}")
            if git(root, "diff", "--cached", "--name-only"):
                raise WorkflowError(f"{name}: the index has changes outside runner ownership")
            git(root, "add", "--", *changed)
            try:
                git(root, "commit", "-m", manifest["delivery"]["commit_message"])
            except WorkflowError:
                git(root, "reset", "--", *changed)
                raise
            progress["commit"] = git(root, "rev-parse", "HEAD")
            save()
        if git(root, "rev-parse", "HEAD") != progress["commit"]:
            raise WorkflowError(f"{name}: HEAD changed after the recorded delivery commit")
        if not progress.get("pushed"):
            git(root, "push", repo["remote"], f"HEAD:refs/heads/{branch}")
            progress["pushed"] = True; save()
        if pull_requests and not progress.get("pr"):
            body = contained(Path(manifest["_directory"]), manifest["delivery"]["body_file"]).read_text()
            progress["pr"] = draft_pr(root, repo, branch, manifest["delivery"]["title"], body)
            save()
    return state.get("delivery", {})

def worktrees(project):
    return {r["id"]: git(project.repo_path(r["id"]), "worktree", "list", "--porcelain") for r in project.profile["repositories"]}

def sync_base(project, names):
    results = {}
    for name in names:
        repo = project.repository(name); root = project.repo_path(name)
        if git(root, "branch", "--show-current") != repo["base_branch"] or git(root, "status", "--porcelain"):
            raise WorkflowError(f"{name}: base checkout must be clean and on {repo['base_branch']}")
        git(root, "fetch", repo["remote"], repo["base_branch"])
        results[name] = git(root, "merge", "--ff-only", "FETCH_HEAD")
    return results
