"""Recoverable, no-overwrite migration of the legacy .agentflow project folder."""
from __future__ import annotations
import base64
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import time
from .util import WorkflowError, atomic_write, digest, json_text, read_json

LEGACY = ".agentflow"
CURRENT = ".plovi"

def checkpoint(phase):
    """Fault boundary used by isolated migration tests."""

def configuration(root):
    root = Path(root)
    old, new = root / LEGACY, root / CURRENT
    for path in (old, new):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise WorkflowError(f"Project configuration must be a directory, not a symlink: {path.name}")
    if old.exists() and new.exists() and old.exists():
        raise WorkflowError("Both .agentflow/ and .plovi/ exist; preserve both and resolve the conflict before retrying.")
    return old if old.exists() else new

def rebase_path(value):
    """Only path components change; arbitrary prose and user file contents do not."""
    if isinstance(value, str):
        import re
        return re.sub(r"(^|[/\\])\.agentflow(?=$|[/\\])", lambda m: m[1] + CURRENT, value)
    return value

def profile_paths(profile):
    import copy
    result = copy.deepcopy(profile)
    for section, keys in (("planning", ("directory", "evidence_directory")),
                          ("git", ("worktree_directory",)),
                          ("extensions", tuple(result.get("extensions", {})))):
        for key in keys:
            if key in result.get(section, {}):
                result[section][key] = rebase_path(result[section][key])
    return result

def ignore_paths(text):
    """Rebase the managed ignore region; retain all custom surrounding patterns."""
    begin, end = "<!-- plovi:start -->", "<!-- plovi:end -->"
    text = text.replace("<!-- agentflow:start -->", begin).replace("<!-- agentflow:end -->", end)
    required = (".plovi/local/", ".plovi/runtime/", ".plovi-migration.lock", ".plovi-migration.json")
    if begin in text:
        if text.count(begin) != 1 or text.count(end) != 1:
            raise WorkflowError("Malformed managed ignore block; repair it before migration")
        before, rest = text.split(begin)
        block, after = rest.split(end)
        lines = [rebase_path(line) for line in block.strip("\n").splitlines()]
        lines += [line for line in required if line not in lines]
        return before + begin + "\n" + "\n".join(lines) + "\n" + end + after
    lines = text.splitlines()
    additions = [line for line in required if line not in lines]
    return text.rstrip() + ("\n" + "\n".join(additions) + "\n" if additions else "\n")


def _changes(root, old):
    changes = {}
    def put_text(path, text):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise WorkflowError("Migration metadata must stay inside its project without symlinks")
        before = path.read_bytes()
        after = text.encode()
        if before != after:
            changes[path.relative_to(root).as_posix()] = {
                "before": base64.b64encode(before).decode(), "after": base64.b64encode(after).decode(),
                "mode": path.stat().st_mode & 0o777}
    def put(path, value):
        put_text(path, json_text(value))
    ignore = root / ".gitignore"
    if ignore.is_file():
        put_text(ignore, ignore_paths(ignore.read_text()))
    for path in (old / "project.json",):
        if path.is_file():
            put(path, profile_paths(read_json(path)))
    baseline = old / "local/setup-baseline.json"
    if baseline.is_file():
        data = read_json(baseline)
        if "profile" in data:
            data["profile"] = profile_paths(data["profile"])
        # Baseline content is generated metadata, not a user file. Preserve the
        # old instruction text so setup can still recognize edited managed blocks.
        data["files"] = {rebase_path(k): v for k, v in data.get("files", {}).items()}
        if ".gitignore" in data["files"]:
            data["files"][".gitignore"] = ignore_paths(data["files"][".gitignore"])
        if LEGACY + "/project.json" in read_json(baseline).get("files", {}):
            key = CURRENT + "/project.json"
            try:
                data["files"][key] = json_text(profile_paths(json.loads(data["files"][key])))
            except (ValueError, TypeError):
                raise WorkflowError("Invalid setup baseline; repair it before migration")
        put(baseline, data)
    active = old / "runtime/active.json"
    if active.is_file():
        data = read_json(active)
        if "path" in data:
            data["path"] = _absolute_path(data["path"], root)
        put(active, data)
    receipt_path = old / "runtime/receipt.json"
    if receipt_path.is_file():
        receipt = read_json(receipt_path)
        receipt["files"] = {_absolute_path(k, root): v for k, v in receipt.get("files", {}).items()}
        for info in receipt.get("versions", {}).values():
            info["path"] = _absolute_path(info["path"], root)
        # Owned launchers may contain absolute pointers; only change bytes that
        # still match their receipt, never user-edited wrappers or old payloads.
        for key, info in receipt["files"].items():
            current = Path(key)
            original = Path(str(current).replace(str(root / CURRENT), str(old), 1)) if current.is_relative_to(root / CURRENT) else current
            if original.is_file() and not original.is_symlink() and digest(original.read_bytes()) == info["sha256"]:
                text = original.read_text(encoding="utf-8")
                changed = text.replace(str(old), str(root / CURRENT))
                if changed != text:
                    relative = original.relative_to(root).as_posix()
                    changes[relative] = {"before": base64.b64encode(text.encode()).decode(),
                                         "after": base64.b64encode(changed.encode()).decode(),
                                         "mode": original.stat().st_mode & 0o777}
                    info["sha256"] = digest(changed)
        put(receipt_path, receipt)
    return changes

def _absolute_path(value, root):
    path = Path(value)
    old = root / LEGACY
    return str(root / CURRENT / path.relative_to(old)) if path.is_relative_to(old) else value

def migrate(root):
    """Move once; roll forward a journal after interruption without losing edits."""
    from .state import lock
    root = Path(root).resolve()
    old, new = root / LEGACY, root / CURRENT
    configuration(root)
    journal = root / ".plovi-migration.json"
    if not old.exists() and not journal.exists():
        return False
    # Lock outside the moved tree. Leave this inode in place so waiting processes
    # cannot acquire different locks after another process unlinks it.
    stack = ExitStack()
    deadline = time.monotonic() + 15
    while True:
        try:
            stack.enter_context(lock(root / ".plovi-migration.lock"))
            break
        except WorkflowError:
            if time.monotonic() >= deadline:
                raise WorkflowError("Project migration is busy; retry after the other process finishes")
            time.sleep(.02)
    with stack:
        configuration(root)
        saved = read_json(journal)
        if not old.exists() and not saved:
            return False
        if saved is None:
            profile = read_json(old / "project.json", {})
            evidence = profile.get("planning", {}).get("evidence_directory", LEGACY + "/local/evidence")
            evidence_path = (root / evidence).resolve()
            if not evidence_path.is_relative_to(root):
                raise WorkflowError("Migration evidence directory leaves the project")
            for state in evidence_path.glob("*/state.json"):
                if read_json(state, {}).get("status") in {"starting", "running", "needs_input"}:
                    raise WorkflowError("Finish or cancel active tasks before migrating the project")
            # Checking the OS-held runner lock also catches live processes whose
            # state has not yet been written.
            runner_lock = old / "local/runner.lock"
            if runner_lock.exists():
                with lock(runner_lock):
                    pass
            saved = {"schema_version": 1, "changes": _changes(root, old)}
            atomic_write(journal, json_text(saved), 0o600)
        checkpoint("before-move")
        if old.exists():
            if new.exists():
                raise WorkflowError("Migration destination already exists; preserve both folders")
            old.rename(new)
        checkpoint("after-move")
        for relative, change in saved["changes"].items():
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise WorkflowError("Invalid migration journal path")
            destination = root / rebase_path(relative)
            if destination.is_symlink() or not destination.resolve().is_relative_to(root):
                raise WorkflowError("Migration metadata path leaves its project")
            before, after = (base64.b64decode(change[k]) for k in ("before", "after"))
            actual = destination.read_bytes()
            if actual not in (before, after):
                raise WorkflowError("Migration metadata changed externally; preserve the journal and resolve the edit before retrying")
            if actual != after:
                atomic_write(destination, after.decode(), change["mode"])
            checkpoint("metadata")
        journal.unlink()
        print("Moved .agentflow/ to .plovi/.", file=sys.stderr)
        return True
