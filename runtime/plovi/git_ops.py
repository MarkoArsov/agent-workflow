"""Repository participation, outcome guards, and resumable delivery mechanics."""
from __future__ import annotations
import os
from pathlib import Path
from .manifest import matches
from .util import WorkflowError, common_dir, contained, digest, git, json_text, run, same_path

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
    from .factory import owns
    factory_run = any(owns(project, name, path) for name, path in checkouts.items())
    for repo in project.profile["repositories"]:
        if factory_run and repo['id'] not in checkouts:
            continue
        root = Path(checkouts.get(repo["id"], project.repo_path(repo["id"])))
        result[repo["id"]] = {"head": git(root, "rev-parse", "HEAD"), "branch": git(root, "branch", "--show-current"),
                              "index": digest(git(root, "ls-files", "--stage", "-z")),
                              "files": files(root)}
        parked = project.repo_path(repo["id"])
        if not same_path(root, parked) and not owns(project, repo['id'], root):
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

def prepare(project, manifest, *, strategies=None):
    from .state import lock
    strategies = strategies or {r['id']: project.repository(r['id'])['checkout_strategy'] for r in manifest['repositories']}
    factory_rows = [r for r in manifest['repositories'] if strategies[r['id']] == 'factory']
    result = {}
    if factory_rows:
        from .factory import allocate
        result.update(allocate(project, manifest['task'], unattended=True, manifest=dict(manifest, repositories=factory_rows)))
    local_rows = [r for r in manifest['repositories'] if strategies[r['id']] != 'factory']
    if local_rows:
        with lock(project.config / 'local/repo-ops.lock', wait=True):
            result.update(_prepare(project, dict(manifest, repositories=local_rows)))
    return result


def _prepare(project, manifest):
    result = {}
    for row in manifest["repositories"]:
        name = row["id"]; repo = project.repository(name); root = project.repo_path(name)
        if row["access"] == "read":
            result[name] = str(root); continue
        from .tasks import owned_checkout
        owned = owned_checkout(project, manifest['task'], name, row.get('branch'))
        if owned is not None:
            if git(Path(owned), "diff", "--cached", "--name-only"):
                raise WorkflowError(f"{name}: existing staged changes must be preserved before execution")
            result[name] = owned
            continue
        strategy = repo["checkout_strategy"]
        branch = row.get("branch")
        if strategy != "current-checkout":
            if not branch or branch == repo["base_branch"]:
                raise WorkflowError(f"{name}: branch strategy requires an explicit feature branch")
            git(root, "check-ref-format", "--branch", branch)
            # Reuse a prepared task worktree even while its plan is being written.
            reusable = strategy == "worktree" and (contained(project.root, project.profile["git"]["worktree_directory"]) / manifest["task"] / name).exists()
            if not reusable and git(root, "status", "--porcelain"):
                raise WorkflowError(f"{name}: commit/stash existing changes before preparing a new checkout")
            exists = bool(git(root, "branch", "--list", branch))
            if strategy == "feature-branch":
                git(root, "switch", *([branch] if exists else ["-c", branch, repo["base_branch"]]))
            else:
                directory = contained(project.root, project.profile["git"]["worktree_directory"])
                target = directory / manifest["task"] / name
                if target.exists():
                    registered = git(root, "worktree", "list", "--porcelain", "-z").split("\0")
                    worktrees = [field.removeprefix("worktree ") for field in registered if field.startswith("worktree ")]
                    if not any(same_path(target, path) for path in worktrees) or common_dir(target) != common_dir(root):
                        raise WorkflowError(f"Existing task worktree has different repository ownership: {target}")
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

def crash_after(point):
    if os.environ.get("PLOVI_TESTING") == "1" and os.environ.get("PLOVI_TEST_CRASH_AFTER") == point:
        os._exit(86)

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
        with __import__('contextlib').ExitStack() as stack:
            from .state import lock
            stack.enter_context(lock(project.config / "local/repo-ops.lock", wait=True))
            from . import factory
            factory_owned = factory.owns(project, name, root)
            remote_url = repo['remote']
            if factory_owned:
                stack.enter_context(lock(factory.safe(factory.root(project), 'repo-ops.lock'), wait=True))
                remote_url = factory._register(project, [name])[name]['push']
            head = git(root, "rev-parse", "HEAD")
            intent = progress.get("intent")
            if not progress.get("commit") and intent and head != intent["baseline_head"]:
                parents = git(root, "show", "-s", "--format=%P", head).split()
                message = git(root, "show", "-s", "--format=%B", head)
                actual_paths = git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", head).splitlines()
                if (parents != [intent["baseline_head"]] or message != intent["message"]
                        or sorted(actual_paths) != intent["paths"]
                        or git(root, "rev-parse", "HEAD^{tree}") != intent["tree"]
                        or git(root, "diff", "--cached", "--name-only")):
                    raise WorkflowError(f"{name}: unexpected HEAD/index; delivery intent cannot be adopted")
                progress["commit"] = head; save()
            if not progress.get("commit"):
                changed = paths[name]
                if not changed:
                    progress["unchanged"] = True; save(); continue
                if set(changed) & set(state["initial_dirty"].get(name, [])):
                    raise WorkflowError(f"{name}: refusing to commit pre-existing user changes")
                if head != baseline[name]["head"]:
                    raise WorkflowError(f"{name}: unexpected HEAD before delivery")
                if git(root, "diff", "--cached", "--name-only"):
                    if not intent or git(root, "write-tree") != intent["tree"]:
                        raise WorkflowError(f"{name}: the index has changes outside runner ownership")
                if not intent:
                    import tempfile
                    with tempfile.TemporaryDirectory(prefix="plovi-index-") as temporary:
                        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / "index"))
                        run(["git", "read-tree", head], root, env=env)
                        run(["git", "add", "--", *changed], root, env=env)
                        tree = run(["git", "write-tree"], root, env=env).stdout.strip()
                    intent = {"baseline_head": head, "paths": sorted(changed),
                              "message": manifest["delivery"]["commit_message"], "tree": tree,
                              "files": {path: current[name]["files"].get(path) for path in changed}}
                    progress["intent"] = intent; save()
                git(root, "add", "--", *changed)
                if git(root, "write-tree") != intent["tree"]:
                    raise WorkflowError(f"{name}: task contents changed after delivery intent")
                try:
                    git(root, "commit", "-m", intent["message"])
                except WorkflowError:
                    git(root, "reset", "--", *changed)
                    raise
                crash_after("commit")
                progress["commit"] = git(root, "rev-parse", "HEAD"); save()
            if git(root, "rev-parse", "HEAD") != progress["commit"]:
                raise WorkflowError(f"{name}: HEAD changed after the recorded delivery commit")
            if git(root, "diff", "--cached", "--name-only"):
                raise WorkflowError(f"{name}: foreign index changes prevent delivery")
            # Query failure is an error, never proof of a missing remote branch.
            remote = git(root, "ls-remote", "--heads", remote_url, f"refs/heads/{branch}")
            remote_head = remote.split()[0] if remote else None
            if remote_head != progress["commit"]:
                if progress.get("pushed"):
                    raise WorkflowError(f"{name}: remote branch diverged after push")
                git(root, '-c', 'remote.origin.mirror=false', "push", remote_url, f"HEAD:refs/heads/{branch}")
                crash_after("push")
            progress["pushed"] = True; save()
        if pull_requests:
            from .evidence import evidence_markdown
            body = evidence_markdown(state, manifest) + "\n\n" + contained(Path(manifest["_directory"]), manifest["delivery"]["body_file"]).read_text()
            progress["pr"] = draft_pr(root, repo, branch, manifest["delivery"]["title"], body)
            crash_after("pr")
            progress["evidence_digest"] = digest(evidence_markdown(state, manifest))
            save()
    return state.get("delivery", {})

def worktrees(project):
    from .factory import worktrees as allocations
    return {'local': {r['id']: git(project.repo_path(r['id']), 'worktree', 'list', '--porcelain') for r in project.profile['repositories']},
            'allocations': allocations(project)}

def sync_base(project, names):
    from .state import lock
    with lock(project.config / "local/repo-ops.lock", wait=True):
        return _sync_base(project, names)

def _sync_base(project, names):
    results = {}
    for name in names:
        repo = project.repository(name); root = project.repo_path(name)
        if git(root, "branch", "--show-current") != repo["base_branch"] or git(root, "status", "--porcelain"):
            raise WorkflowError(f"{name}: base checkout must be clean and on {repo['base_branch']}")
        git(root, "fetch", repo["remote"], repo["base_branch"])
        results[name] = git(root, "merge", "--ff-only", "FETCH_HEAD")
    return results
