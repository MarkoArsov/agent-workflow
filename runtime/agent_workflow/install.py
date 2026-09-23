"""Versioned payloads and receipt-owned adapters; project extensions are never inputs."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from .detect import repositories
from .extensions import catalog
from .util import WorkflowError, atomic_write, digest, file_hash, json_text, package_root, read_json, user_data, write_json

PAYLOAD = ("workflow-package.json", "package-files.json", "LICENSE", "README.md", "pyproject.toml", "bin", "runtime",
           "skills", "references", "schemas", "templates", ".claude-plugin", "install.py", "install.sh")
IGNORE = {"__pycache__", ".DS_Store", ".git", ".venv", "node_modules"}

def files_in(source):
    for name in PAYLOAD:
        path = source / name
        if not path.exists():
            continue
        items = [path] if path.is_file() else sorted(path.rglob("*"))
        for item in items:
            if any(p in IGNORE for p in item.relative_to(source).parts):
                continue
            if item.is_symlink():
                raise WorkflowError("Distribution payloads must not contain symlinks")
            if item.is_file():
                yield item

def payload_digest(source):
    return digest(json_text({str(p.relative_to(source)): file_hash(p) for p in files_in(source)}))

def validate_source(source):
    marker = read_json(source / "workflow-package.json")
    if not marker or marker.get("name") != "agent-workflow" or marker.get("schema_version") != 1:
        raise WorkflowError("Not a compatible agent-workflow package")
    version = marker.get("version", "")
    from .util import identifier
    identifier(version)
    for required in ("bin/agent-workflow", "runtime/agent_workflow/cli.py", "skills/project-setup/SKILL.md"):
        if not (source / required).is_file():
            raise WorkflowError(f"Package is missing {required}")
    catalog(package=source)
    checksums = read_json(source / "package-files.json")
    if checksums is not None:
        observed = {str(p.relative_to(source)): file_hash(p) for p in files_in(source) if p.name != "package-files.json"}
        if checksums != observed:
            raise WorkflowError("Package checksum manifest does not match the payload")
    return marker

def installation_root(project=None):
    return Path(project).expanduser().resolve() / ".agent-workflow/runtime" if project else user_data()

def wrappers(source, project, agents):
    template = (source / "templates/adapters/dispatch.py").read_text()
    result = {}
    if project:
        roots = repositories(project)
        locations = [(p / ".agents/skills") for p in (roots or [project])] if set(agents) & {"codex", "cursor"} else []
        if "claude" in agents:
            locations += [(p / ".claude/skills") for p in (roots or [project])]
    else:
        locations = [Path.home() / ".agents/skills"] if set(agents) & {"codex", "cursor"} else []
        if "claude" in agents:
            locations += [Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / "skills"]
    for location in locations:
        for name, info in catalog(package=source).items():
            folder = location / ("aw-" + name)
            result[folder / "SKILL.md"] = f"---\nname: aw-{name}\ndescription: {json.dumps(info['description'])}\n---\n\nRun this skill folder's scripts/dispatch.py with the current project as its working directory. Read the returned effective skill file, then follow its procedure. Project overrides take precedence. Do not use defaults from another project.\n"
            result[folder / "scripts/dispatch.py"] = template.replace("SKILL_NAME = None", f"SKILL_NAME = {name!r}")
    return result

def install(source, *, project=None, agents=None, dry_run=False):
    source = Path(source).expanduser().resolve()
    project = Path(project).expanduser().resolve() if project else None
    if project and not project.is_dir():
        raise WorkflowError("Create/select the project directory before installing")
    marker = validate_source(source)
    root = installation_root(project)
    version = marker["version"]
    target = root / "versions" / version
    receipt_path = root / "receipt.json"
    receipt_before = file_hash(receipt_path)
    receipt = read_json(receipt_path, {"files": {}, "versions": {}})
    profile_path = project / ".agent-workflow/project.json" if project else None
    profile = read_json(profile_path) if profile_path else None
    agents = agents or (profile.get("agents") if profile else None) or receipt.get("agents") or ["claude", "codex", "cursor"]
    desired = wrappers(source, project, agents)
    launcher = project / ".agent-workflow/bin/agent-workflow" if project else Path.home() / ".local/bin/agent-workflow"
    code = (source / "templates/adapters/launch.py").read_text()
    if project:
        code = code.replace("LOCAL_RUNTIME = None", "LOCAL_RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'")
    desired[launcher] = code
    if project:
        desired[root / ".gitignore"] = "*\n"
    conflicts = []
    for path, content in desired.items():
        previous = receipt["files"].get(str(path))
        if path.exists() and file_hash(path) != digest(content) and (not previous or file_hash(path) != previous["sha256"]):
            conflicts.append(str(path))
    obsolete = [Path(p) for p in receipt["files"] if Path(p) not in desired]
    for path in obsolete:
        if path.exists() and file_hash(path) != receipt["files"][str(path)]["sha256"]:
            conflicts.append(str(path))
    content_hash = payload_digest(source)
    if target.exists() and payload_digest(target) != content_hash:
        conflicts.append(f"Version {version} already has different content; use a new package version")
    if profile and profile.get("schema_version") != marker["schema_version"]:
        conflicts.append("Project profile needs a schema migration before this package can activate")
    result = {"mode": "project" if project else "global", "version": version, "target": str(target),
              "files": [str(p) for p in desired], "conflicts": conflicts, "dry_run": dry_run}
    if dry_run:
        return result
    if conflicts:
        raise WorkflowError("Installation conflicts; preserve/resolve these files first:\n" + "\n".join(conflicts))
    root.mkdir(parents=True, exist_ok=True)
    from .state import lock
    with lock(root / "install.lock"):
        if file_hash(receipt_path) != receipt_before:
            raise WorkflowError("Installation changed during preparation; retry the reviewed update")
        backup_paths = set(desired) | set(obsolete) | {root / "active.json", receipt_path}
        if profile_path and profile:
            backup_paths |= {profile_path, project / ".agent-workflow/package-lock.json"}
        backups = {p: p.read_bytes() if p.is_file() else None for p in backup_paths}
        created_version = False
        try:
            if not target.exists():
                (root / "versions").mkdir(exist_ok=True)
                staging = Path(tempfile.mkdtemp(prefix=".stage-", dir=root / "versions"))
                try:
                    for path in files_in(source):
                        destination = staging / path.relative_to(source)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, destination)
                    if payload_digest(staging) != content_hash:
                        raise WorkflowError("Staged package integrity mismatch")
                    os.replace(staging, target); created_version = True
                finally:
                    if staging.exists():
                        shutil.rmtree(staging)
            for path, content in desired.items():
                atomic_write(path, content, 0o755 if path == launcher else None)
            for path in obsolete:
                path.unlink(missing_ok=True)
            if profile:
                profile["package"]["version"] = version
                write_json(profile_path, profile)
                write_json(project / ".agent-workflow/package-lock.json", {"version": version, "schema_version": 1})
            write_json(root / "active.json", {"version": version, "path": str(target), "backend": "standalone"})
            versions = dict(receipt.get("versions", {}))
            versions[version] = {"path": str(target), "sha256": content_hash}
            write_json(receipt_path, {"schema_version": 1, "backend": "standalone", "version": version,
                                      "mode": result["mode"], "project": str(project) if project else None, "agents": agents,
                                      "versions": versions,
                                      "files": {str(p): {"sha256": file_hash(p)} for p in desired}})
        except BaseException:
            for path, content in backups.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
            if created_version:
                shutil.rmtree(target)
            raise
    result["override_updates"] = override_updates(project, target) if project else []
    result["next"] = "Run aw-project-setup in your agent, or agent-workflow setup PATH."
    return result

def override_updates(project, package):
    if not project:
        return []
    lock = read_json(project / ".agent-workflow/overrides.lock.json", {})
    updates = []
    for name, base in lock.items():
        current = package / "skills" / name / "SKILL.md"
        if current.is_file() and file_hash(current) != base["sha256"]:
            updates.append({"skill": name, "base_version": base["version"], "upstream_sha256": file_hash(current),
                            "action": "Review upstream changes; project override is preserved"})
    return updates

def uninstall(*, project=None, dry_run=False):
    project = Path(project).expanduser().resolve() if project else None
    root = installation_root(project)
    receipt = read_json(root / "receipt.json")
    if not receipt:
        raise WorkflowError("No standalone installation receipt; use native plugin uninstall for plugin-owned installs")
    remove, preserve = [], []
    for name, owned in receipt["files"].items():
        path = Path(name)
        if not path.exists():
            continue
        (remove if file_hash(path) == owned["sha256"] else preserve).append(path)
    versions = []
    for version, data in receipt["versions"].items():
        path = Path(data["path"])
        if path.exists():
            if path.resolve().parent != (root / "versions").resolve():
                raise WorkflowError("Receipt version leaves its installation root")
            if payload_digest(path) == data["sha256"]:
                versions.append(path)
            else:
                preserve.append(path)
    result = {"remove": [str(p) for p in remove + versions], "preserve_modified": [str(p) for p in preserve], "dry_run": dry_run}
    if dry_run:
        return result
    from .state import lock
    with lock(root / "install.lock"):
        for path in remove:
            path.unlink()
            parent = path.parent
            while parent.name.startswith("aw-") or parent.name == "scripts":
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
        for path in versions:
            shutil.rmtree(path)
        (root / "active.json").unlink(missing_ok=True)
        if preserve:
            write_json(root / "uninstall-preserved.json", result)
        (root / "receipt.json").unlink(missing_ok=True)
    return result

def doctor(project=None):
    root = installation_root(project)
    receipt = read_json(root / "receipt.json", {})
    native = []
    native_error = None
    if shutil.which("claude"):
        try:
            from .util import run
            listed = json.loads(run(["claude", "plugin", "list", "--json"], Path(project) if project else Path.cwd(), timeout=10).stdout)
            native = [{k: item.get(k) for k in ("id", "version", "scope", "enabled", "installPath")}
                      for item in listed if item.get("id") == "agent-workflow@agent-workflow"]
        except (WorkflowError, ValueError, TypeError) as exc:
            native_error = str(exc)
    return {"root": str(root), "active": read_json(root / "active.json"), "backend": receipt.get("backend"),
            "modified_owned_files": [p for p, info in receipt.get("files", {}).items() if file_hash(Path(p)) != info["sha256"]],
            "native_plugins": native, "native_inspection_error": native_error,
            "duplicate_claude_backends": bool(native and receipt.get("backend") and "claude" in receipt.get("agents", [])),
            "project_extensions": "Preserved outside the installed payload"}

def main(argv=None):
    parser = argparse.ArgumentParser(description="Install agent-workflow without pip.")
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument("--global", dest="global_install", action="store_true")
    location.add_argument("--project", type=Path)
    parser.add_argument("--local-source", type=Path, default=package_root())
    parser.add_argument("--agents", nargs="+", choices=["claude", "codex", "cursor"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json_text(install(args.local_source, project=args.project, agents=args.agents, dry_run=args.dry_run)))
    except (WorkflowError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")
