"""Small filesystem and process primitives shared by the package."""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

class WorkflowError(Exception):
    """An actionable configuration or execution failure."""

def package_root() -> Path:
    return Path(__file__).resolve().parents[2]

def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise WorkflowError(f"Cannot read {path}: {exc}") from exc

def json_text(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()

def file_hash(path: Path) -> str | None:
    return digest(path.read_bytes()) if path.is_file() else None

def atomic_write(path: Path, content: str, mode: int | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, mode if mode is not None else (path.stat().st_mode & 0o777 if path.exists() else 0o644))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def write_json(path: Path, value):
    atomic_write(path, json_text(value))

def contained(root: Path, relative: str, *, allow_root: bool = True) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or (not allow_root and candidate == root.resolve()):
        raise WorkflowError(f"Path leaves its allowed root: {relative}")
    return candidate

def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", value):
        raise WorkflowError(f"Invalid identifier: {value!r}")
    return value

def run(argv, cwd: Path, *, check=True, timeout=60, env=None):
    try:
        result = subprocess.run([str(x) for x in argv], cwd=cwd, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkflowError(f"Cannot run {argv[0]}: {exc}") from exc
    if check and result.returncode:
        raise WorkflowError(f"{argv[0]} failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}")
    return result

def git(root: Path, *args, check=True) -> str:
    return run(["git", "-C", root, *args], root, check=check).stdout.strip()

def common_dir(root: Path) -> Path | None:
    result = run(["git", "rev-parse", "--git-common-dir"], root, check=False)
    if result.returncode:
        return None
    return (root / result.stdout.strip()).resolve()

def user_data() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "agent-workflow"

def redact(text: str) -> str:
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[redacted]", text)
    text = re.sub(r"(?i)((?:token|password|secret|api[_-]?key)\s*[=:]\s*)[^\s,;]+", r"\1[redacted]", text)
    return re.sub(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})", "[redacted]", text)

