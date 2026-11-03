"""Keep a linked development install current without manual steps.

A linked global install runs plovi straight from a source checkout. After a pull
request merges, two things used to be manual: updating that checkout and
refreshing skill discovery. This module does both:

- discovery is refreshed in the foreground whenever the checkout's skills,
  adapters or package metadata change (a cheap content fingerprint);
- at most once per interval, a detached background process fetches the remote
  base and fast-forwards the checkout, but only when it is on that branch, has
  no tracked changes and has no local commits of its own.

Nothing here ever fails the command the person ran. Problems become a one-line
note on stderr, shown once.
"""
from __future__ import annotations
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path
from .util import WorkflowError, package_root, read_json, write_json

STATE_FILE = "self-update.json"
DEFAULTS = {"follow": True, "remote": "origin", "branch": None, "interval_minutes": 60}
OFF = "PLOVI_NO_SELF_UPDATE"


def _root():
    from .install import installation_root
    return installation_root(migrate=False)


def state_path():
    return _root() / STATE_FILE


def load():
    value = read_json(state_path(), {}) or {}
    return {**DEFAULTS, **value} if isinstance(value, dict) else dict(DEFAULTS)


def save(value):
    write_json(state_path(), value)


def linked_source():
    """The linked checkout, when the running code is that checkout; otherwise None."""
    receipt = read_json(_root() / "receipt.json", {}) or {}
    if receipt.get("backend") != "linked" or not receipt.get("source"):
        return None
    source = Path(receipt["source"])
    try:
        return source if source.resolve() == package_root().resolve() else None
    except OSError:
        return None


def fingerprint(source: Path) -> str:
    """Hash everything global discovery is generated from."""
    digest = hashlib.sha256()
    paths = [source / "workflow-package.json", *sorted((source / "skills").glob("*/SKILL.md")),
             *sorted(p for p in (source / "templates/adapters").rglob("*") if p.is_file())]
    for path in paths:
        try:
            data = path.read_bytes()
        except OSError:
            data = b""
        digest.update(path.relative_to(source).as_posix().encode() + b"\0" + hashlib.sha256(data).digest())
    return digest.hexdigest()


def refresh_discovery(source: Path, value: dict, notes: list) -> dict | None:
    current = fingerprint(source)
    if value.get("discovery") == current:
        return None
    from .install import sync_linked
    try:
        result = sync_linked()
    except (WorkflowError, OSError) as exc:
        notes.append(f"plovi: could not refresh skill discovery ({exc}). Run: python3 install.py --global --sync")
        return {"status": "failed", "detail": str(exc)}
    value["discovery"] = current
    if result.get("status") != "unchanged":
        notes.append("plovi: refreshed skill discovery from the linked checkout.")
    return result


def _git(source, *args, timeout=60):
    result = subprocess.run(["git", "-C", str(source), *args], capture_output=True, text=True, timeout=timeout,
                            stdin=subprocess.DEVNULL)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _branch(source, value):
    if value.get("branch"):
        return value["branch"]
    code, out, _ = _git(source, "symbolic-ref", "--short", f"refs/remotes/{value['remote']}/HEAD")
    return out.split("/", 1)[1] if code == 0 and "/" in out else "main"


def update_checkout(source: Path, value: dict) -> dict:
    """Fetch and fast-forward the linked checkout when that is safe."""
    remote = value["remote"]
    if not (source / ".git").exists():
        return {"status": "skipped", "detail": "The linked folder is not a Git checkout."}
    branch = _branch(source, value)
    target = f"{remote}/{branch}"
    code, _, err = _git(source, "fetch", "--quiet", remote, f"+refs/heads/{branch}:refs/remotes/{target}")
    if code:
        return {"status": "fetch_failed", "detail": err.splitlines()[-1] if err else "git fetch failed"}
    _, current, _ = _git(source, "rev-parse", "--abbrev-ref", "HEAD")
    _, behind, _ = _git(source, "rev-list", "--count", f"HEAD..{target}")
    _, ahead, _ = _git(source, "rev-list", "--count", f"{target}..HEAD")
    behind, ahead = int(behind or 0), int(ahead or 0)
    if behind == 0:
        return {"status": "current", "branch": branch}
    if current != branch:
        return {"status": "behind", "behind": behind, "branch": branch,
                "detail": f"The linked checkout is on {current}, not {branch}."}
    _, dirty, _ = _git(source, "status", "--porcelain", "--untracked-files=no")
    if dirty:
        return {"status": "behind", "behind": behind, "branch": branch, "detail": "It has uncommitted changes."}
    if ahead:
        return {"status": "behind", "behind": behind, "branch": branch,
                "detail": f"It has {ahead} local commit(s) that are not on {target}."}
    code, _, err = _git(source, "merge", "--ff-only", "--quiet", target)
    if code:
        return {"status": "behind", "behind": behind, "branch": branch, "detail": err or "Fast-forward failed."}
    return {"status": "updated", "commits": behind, "branch": branch}


def run_update(source: Path) -> dict:
    """The background job: update the checkout, then refresh discovery."""
    from .state import lock
    with lock(_root() / "self-update.lock"):
        value = load()
        value["last_fetch"] = time.time()
        result = update_checkout(source, value)
        result["at"] = time.time()
        value["last_result"] = result
        value["shown"] = False
        notes = []
        if result["status"] == "updated":
            refresh_discovery(source, value, notes)
        save(value)
        return result


def _due(value, now):
    return value.get("follow") and now - float(value.get("last_fetch") or 0) >= 60 * float(value["interval_minutes"])


def _start_background(source: Path):
    from .process import detached
    log = _root() / "self-update.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as handle:
        subprocess.Popen([sys.executable, str(source / "bin/plovi"), "self-update", "--background"],
                         stdin=subprocess.DEVNULL, stdout=handle, stderr=handle, cwd=str(source), **detached())


def _note_for(result):
    if result.get("status") == "updated":
        return f"plovi: updated the linked checkout by {result['commits']} commit(s) from {result['branch']}."
    if result.get("status") == "behind":
        return (f"plovi: the linked checkout is {result['behind']} commit(s) behind {result['branch']}. "
                f"{result.get('detail', '')} Update it with git pull.").replace("  ", " ")
    if result.get("status") == "fetch_failed":
        return f"plovi: could not check for updates ({result.get('detail')})."
    return None


def maybe_refresh(stream=None):
    """Called at the start of every CLI command. Never raises."""
    stream = stream or sys.stderr
    try:
        if os.environ.get(OFF):
            return
        source = linked_source()
        if source is None:
            return
        value = load()
        notes = []
        now = time.time()
        refresh_discovery(source, value, notes)
        last = value.get("last_result") or {}
        if last and not value.get("shown"):
            note = _note_for(last)
            if note:
                notes.append(note)
            value["shown"] = True
        start = _due(value, now) and (source / ".git").exists()
        if start:
            value["last_fetch"] = now
        save(value)
        if start:
            _start_background(source)
        for note in notes:
            print(note, file=stream)
    except Exception as exc:  # noqa: BLE001 - a helper must never break the person's command
        try:
            print(f"plovi: self-update skipped ({exc}).", file=stream)
        except Exception:  # noqa: BLE001
            pass


def command(args) -> dict:
    """plovi self-update [--now] [--follow on|off] [--interval MINUTES] [--background]."""
    source = linked_source()
    if source is None:
        raise WorkflowError("This plovi is not a linked install of this checkout; self-update only manages "
                            "`python3 install.py --global --link` installs. Reinstall to update a copied install.")
    value = load()
    changed = False
    if args.follow is not None:
        value["follow"] = args.follow == "on"
        changed = True
    if args.interval is not None:
        if args.interval < 5:
            raise WorkflowError("Use an interval of 5 minutes or more")
        value["interval_minutes"] = args.interval
        changed = True
    if changed:
        save(value)
    if args.background or args.now:
        result = run_update(source)
        if args.now:
            value = load()
            refresh_discovery(source, value, [])
            save(value)
        return {"source": str(source), "result": result, **{k: load().get(k) for k in ("follow", "interval_minutes")}}
    return {"source": str(source), **{k: value.get(k) for k in ("follow", "remote", "branch", "interval_minutes",
                                                                  "last_fetch", "last_result")}}
