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
_warned_conflicts = set()

def checkpoint(phase):
    """Fault boundary used by isolated migration tests."""

def relocate_imports(old, new):
    """Keep a copied runtime importable when its containing directory moves."""
    import importlib
    from importlib.machinery import ModuleSpec, SourceFileLoader
    def moved(value):
        if isinstance(value, str):
            path = Path(value)
            if path.is_absolute() and path.is_relative_to(old):
                return str(new / path.relative_to(old))
        return value
    sys.path[:] = [moved(value) for value in sys.path]
    for module in list(sys.modules.values()):
        data = vars(module) if module is not None else {}
        if "__file__" in data:
            data["__file__"] = moved(data["__file__"])
        if "__path__" in data:
            data["__path__"] = [moved(value) for value in data["__path__"]]
        spec = data.get("__spec__")
        if isinstance(spec, ModuleSpec):
            spec.origin = moved(spec.origin)
            if spec.submodule_search_locations is not None:
                spec.submodule_search_locations = [moved(value) for value in spec.submodule_search_locations]
            if isinstance(spec.loader, SourceFileLoader):
                spec.loader.path = moved(spec.loader.path)
    importlib.invalidate_caches()


def configuration(root):
    root = Path(root)
    old, new = root / LEGACY, root / CURRENT
    if new.is_dir() and not new.is_symlink() and (new / "project.json").is_file():
        if (old.exists() or old.is_symlink()) and root not in _warned_conflicts:
            print("Both .agentflow/ and .plovi/ exist; using .plovi/ and preserving .agentflow/.", file=sys.stderr)
            _warned_conflicts.add(root)
        return new
    for path in (old, new):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise WorkflowError(f"Project configuration must be a directory, not a symlink: {path.name}")
    if old.exists() and new.exists() and old.exists():
        raise WorkflowError("Both .agentflow/ and .plovi/ exist without a canonical profile; preserve both and resolve the conflict before retrying.")
    return old if old.exists() else new


def lock_held(path):
    """Probe an existing OS lock without writing its PID or trusting stale state."""
    from .state import _acquire, _release
    try:
        with Path(path).open("r+b") as handle:
            try:
                _acquire(handle)
            except OSError:
                return True
            _release(handle)
    except FileNotFoundError:
        pass
    return False


def task_locks(config):
    profile = read_json(config / "project.json", {})
    evidence = profile.get("planning", {}).get("evidence_directory", config.name + "/local/evidence")
    parts = Path(evidence).parts
    if parts and parts[0] in {CURRENT, LEGACY}:
        evidence = str(Path(config.name, *parts[1:]))
    from .util import contained
    return contained(config.parent, evidence).glob("*/runner.lock")


def worktree_repairs(root, old):
    from .util import run
    profile = read_json(old / "project.json", {})
    repairs = []
    for repo in profile.get("repositories", []):
        location = (root / repo["path"]).resolve()
        if not location.is_relative_to(root):
            raise WorkflowError("Registered repository leaves its project")
        result = run(["git", "worktree", "list", "--porcelain"], location, check=False)
        if result.returncode:
            continue
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                path = Path(line[len("worktree "):])
                if path.is_relative_to(old):
                    repairs.append({"repository": repo["path"], "path": (Path(CURRENT) / path.relative_to(old)).as_posix()})
    return repairs

def rebase_path(value):
    """Only path components change; arbitrary prose and user file contents do not."""
    if isinstance(value, str):
        import re
        return re.sub(r"(^|[/\\])\.agentflow(?=$|[/\\])", lambda m: m[1] + CURRENT, value)
    return value

def profile_paths(profile):
    """Rebase rooted path values in the profile, preserving embedded prose."""
    def visit(value):
        if isinstance(value, str):
            for separator in ("/", "\\"):
                if value.startswith(LEGACY + separator):
                    return CURRENT + value[len(LEGACY):]
            return value
        if isinstance(value, dict):
            return {key: visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        return value
    return visit(profile)

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
        original = block.strip("\n").splitlines()
        lines = list(dict.fromkeys([*original, *(rebase_path(line) for line in original)]))
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
    selected = configuration(root)
    if selected == new and old.exists():
        return False
    journal = root / ".plovi-migration.json"
    if not old.exists() and not journal.exists():
        return False
    if old.exists() and any(lock_held(path) for path in task_locks(old)):
        raise WorkflowError("Finish or cancel active tasks before migrating; a task lock is held")
    if old.exists() and lock_held(old / "local/runner.lock"):
        raise WorkflowError("Finish or cancel active tasks before migrating the project; its run lock is held")
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
        if configuration(root) == new and old.exists():
            return False
        saved = read_json(journal)
        if not old.exists() and not saved:
            return False
        if saved is None:
            profile = read_json(old / "project.json", {})
            evidence = profile.get("planning", {}).get("evidence_directory", LEGACY + "/local/evidence")
            evidence_path = (root / evidence).resolve()
            if not evidence_path.is_relative_to(root):
                raise WorkflowError("Migration evidence directory leaves the project")
            if any(lock_held(path) for path in task_locks(old)):
                raise WorkflowError("Finish or cancel active tasks before migrating; a task lock is held")
            if lock_held(old / "local/runner.lock"):
                raise WorkflowError("Finish or cancel active tasks before migrating the project; its run lock is held")
            saved = {"schema_version": 1, "changes": _changes(root, old), "worktrees": worktree_repairs(root, old)}
            atomic_write(journal, json_text(saved), 0o600)
        checkpoint("before-move")
        if old.exists():
            if new.exists():
                raise WorkflowError("Migration destination already exists; preserve both folders")
            try:
                import os
                os.replace(old, new)
            except OSError as exc:
                raise WorkflowError("Could not rename .agentflow/ to .plovi/. Close open files and retry; preserve the migration journal for recovery.") from exc
        relocate_imports(old, new)
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
        from .util import run
        for repair in saved.get("worktrees", []):
            repository = (root / repair["repository"]).resolve()
            moved = (root / repair["path"]).resolve()
            if not repository.is_relative_to(root) or not moved.is_relative_to(new):
                raise WorkflowError("Worktree repair leaves the project; preserve the migration journal")
            run(["git", "worktree", "repair", str(moved)], repository)
        journal.unlink()
        print("Moved .agentflow/ to .plovi/ (one-time rename).", file=sys.stderr)
        return True


def migrate_user_data(base):
    """Move legacy global state once and rebase only receipt-owned metadata."""
    import os
    from .state import lock
    base = Path(base).expanduser().resolve()
    current = base / "plovi"
    journal = base / ".plovi-data-migration.json"
    if current.is_symlink():
        raise WorkflowError("The plovi user-data location is a symlink; resolve it before migrating")
    if current.exists() and not journal.exists():
        return current
    candidates = [base / name for name in ("agentflow", "agent-workflow") if (base / name).exists()]
    if not candidates and not journal.exists():
        return current
    if len(candidates) > 1 and not journal.exists():
        raise WorkflowError("Both legacy user-data folders exist; preserve both and select the one to migrate")
    base.mkdir(parents=True, exist_ok=True)
    with lock(base / ".plovi-data-migration.lock"):
        saved = read_json(journal)
        if current.exists() and saved is None:
            return current
        if saved is None:
            legacy = candidates[0]
            if legacy.is_symlink() or not legacy.is_dir():
                raise WorkflowError("Legacy user data must be a directory, not a symlink")
            for held in (legacy / "install.lock", legacy / "models/write.lock"):
                if lock_held(held):
                    raise WorkflowError("User-data migration is busy; finish the active update and retry")
            changes = []
            def rebase(value):
                if isinstance(value, str):
                    path = Path(value)
                    if path.is_absolute() and path.is_relative_to(legacy):
                        return str(current / path.relative_to(legacy))
                return value
            def add(path, content, destination=None):
                before = path.read_bytes()
                after = content.encode()
                if before != after:
                    changes.append({"path": str(destination or path), "before": base64.b64encode(before).decode(),
                                    "after": base64.b64encode(after).decode(), "mode": path.stat().st_mode & 0o777})
            receipt_path = legacy / "receipt.json"
            receipt = read_json(receipt_path)
            if receipt:
                receipt["files"] = {rebase(key): value for key, value in receipt.get("files", {}).items()}
                for key in ("source", "project"):
                    if key in receipt:
                        receipt[key] = rebase(receipt[key])
                for info in receipt.get("versions", {}).values():
                    info["path"] = rebase(info["path"])
                for name, info in receipt["files"].items():
                    destination = Path(name)
                    original = legacy / destination.relative_to(current) if destination.is_relative_to(current) else destination
                    if original.is_file() and not original.is_symlink() and digest(original.read_bytes()) == info["sha256"]:
                        code = original.read_text(encoding="utf-8")
                        updated = code.replace(str(legacy), str(current))
                        # Older generated adapters select their data root before
                        # importing a runtime. Only receipt-owned bytes change.
                        updated = updated.replace('/ "' + legacy.name + '"', '/ "plovi"')
                        updated = updated.replace("/ '" + legacy.name + "'", "/ 'plovi'")
                        if updated != code:
                            add(original, updated, destination)
                            info["sha256"] = digest(updated)
                add(receipt_path, json_text(receipt), current / "receipt.json")
            active = legacy / "active.json"
            if active.is_file():
                data = read_json(active)
                if "path" in data:
                    data["path"] = rebase(data["path"])
                add(active, json_text(data), current / "active.json")
            saved = {"schema_version": 1, "legacy": legacy.name, "changes": changes}
            atomic_write(journal, json_text(saved), 0o600)
        legacy = base / saved["legacy"]
        if legacy.name not in {"agentflow", "agent-workflow"}:
            raise WorkflowError("Invalid user-data migration journal")
        if legacy.exists():
            if current.exists():
                raise WorkflowError("Both user-data directories exist; preserve them and the recovery journal")
            try:
                os.replace(legacy, current)
            except OSError as exc:
                raise WorkflowError("Could not rename user data. Close open files and retry; the recovery journal is preserved.") from exc
        relocate_imports(legacy, current)
        for change in saved["changes"]:
            path = Path(change["path"])
            before, after = (base64.b64decode(change[key]) for key in ("before", "after"))
            if path.is_symlink() or path.read_bytes() not in (before, after):
                raise WorkflowError("User-data migration metadata changed externally; preserve the journal and resolve the edit")
            if path.read_bytes() != after:
                atomic_write(path, after.decode(), change["mode"])
        journal.unlink()
        print(f"Moved {saved['legacy']} user data to plovi (one-time rename).", file=sys.stderr)
    return current
