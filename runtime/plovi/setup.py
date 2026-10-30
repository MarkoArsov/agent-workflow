"""Preview-first setup, keyed three-way merge, and stale-proposal protection."""
from __future__ import annotations
import copy
import difflib
import json
import os
from pathlib import Path
from . import __version__
from .detect import scan
from .profile import validate
from .util import WorkflowError, atomic_write, contained, digest, file_hash, json_text, read_json, write_json

MISSING = object()
BEGIN, END = "<!-- plovi:start -->", "<!-- plovi:end -->"

def merge(base, current, detected, path="", resolutions=None):
    resolutions = resolutions or {}
    conflicts = []
    if path in resolutions:
        selected = detected if resolutions[path] == "detected" else current
        return (selected if selected is MISSING else copy.deepcopy(selected)), []
    if current == base:
        return (detected if detected is MISSING else copy.deepcopy(detected)), []
    if detected == base or current == detected:
        return (current if current is MISSING else copy.deepcopy(current)), []
    if base is MISSING:
        if current is MISSING:
            return copy.deepcopy(detected), []
        return copy.deepcopy(current), []
    if all(isinstance(x, dict) for x in (base, current, detected)):
        result = {}
        for key in sorted(base.keys() | current.keys() | detected.keys()):
            value, sub = merge(base.get(key, MISSING), current.get(key, MISSING), detected.get(key, MISSING), path + "/" + key, resolutions)
            if value is not MISSING:
                result[key] = value
            conflicts += sub
        return result, conflicts
    if all(isinstance(x, list) and all(isinstance(v, dict) and "id" in v for v in x) for x in (base, current, detected)):
        maps = [{x["id"]: x for x in items} for items in (base, current, detected)]
        merged, conflicts = merge(*maps, path, resolutions)
        order = [x["id"] for x in current] + [x["id"] for x in detected if x["id"] not in maps[1]]
        return [merged[k] for k in dict.fromkeys(order) if k in merged], conflicts
    conflicts.append({"path": path, "reason": "Both your configuration and detection changed; choose current or detected."})
    return (current if current is MISSING else copy.deepcopy(current)), conflicts

def overlay(base, patch):
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = overlay(result[key], value)
        elif isinstance(value, list) and value and all(isinstance(x, dict) and "id" in x for x in value) and isinstance(result.get(key), list):
            originals = {x["id"]: x for x in result[key]}
            for item in value:
                originals[item["id"]] = overlay(originals.get(item["id"], {}), item)
            result[key] = list(originals.values())
        else:
            result[key] = copy.deepcopy(value)
    return result

def managed(existing: str, block: str) -> str:
    # Legacy managed markers are replaced in place; preserve surrounding prose.
    existing = existing.replace("<!-- agentflow:start -->", BEGIN).replace("<!-- agentflow:end -->", END)
    marked = BEGIN + "\n" + block.rstrip() + "\n" + END
    if BEGIN in existing:
        if END not in existing or existing.count(BEGIN) != 1 or existing.count(END) != 1:
            raise WorkflowError("Malformed managed instruction block; repair it before setup")
        before, remainder = existing.split(BEGIN)
        _, after = remainder.split(END)
        return before + marked + after
    return existing.rstrip() + ("\n\n" if existing.strip() else "") + marked + "\n"

def generated(root: Path, profile: dict) -> dict[str, str]:
    rows = "\n".join(f"- {r['id']}: {r['path']}; {', '.join(r['roles'])}; {r['checkout_strategy']}; participate {r['task_policy']}." for r in profile["repositories"])
    guidance = f"# Project workflow\n\n{rows}\n\nPlans: {profile['planning']['directory']}/<task>/. Commit complete plans: {profile['planning'].get('commit_plans', True)}.\nExecution: {profile['execution']['permission_mode']}. Tracker: {profile['tracking']['provider']}.\nProject skills, rules, and connectors live under .plovi/.\nResolve this project's profile before using workflow defaults. Native instructions and explicit user requests take precedence."
    result = {
        ".plovi/project.json": json_text(profile),
        ".plovi/package-lock.json": json_text({"version": profile["package"]["version"]}),
        "PROJECT_WORKFLOW.md": managed((root / "PROJECT_WORKFLOW.md").read_text() if (root / "PROJECT_WORKFLOW.md").exists() else "", guidance),
        ".gitignore": managed((root / ".gitignore").read_text() if (root / ".gitignore").exists() else "", ".plovi/local/\n.plovi/runtime/\n.plovi-migration.lock\n.plovi-migration.json"),
    }
    from .policy import template
    result["plovi.toml"] = template()
    for repo in profile["repositories"]:
        path = contained(root, repo["path"])
        relative = path.relative_to(root)
        if path != root:
            result[(relative / ".plovi/project-ref.json").as_posix()] = json_text({"root": os.path.relpath(root, path)})
        for name in ("AGENTS.md", "CLAUDE.md"):
            destination = path / name
            old = destination.read_text() if destination.exists() else ""
            link = os.path.relpath(root / "PROJECT_WORKFLOW.md", path)
            result[(relative / name).as_posix()] = managed(old, f"Read {link} for this project's workflow defaults and custom skills.\nDo not apply workflow defaults from an unrelated ancestor project.")
    return result

def propose(root: Path, answers: dict | None = None) -> dict:
    answers = answers or {}
    detected = scan(root)
    root = Path(detected["root"])
    from .migration import configuration, CURRENT, LEGACY, _changes
    import base64
    config = configuration(root)
    pending = config.name == LEGACY
    predicted = _changes(root, config) if pending else {}
    migration_roots = ["."] if pending else []
    aliases = {CURRENT + "/": LEGACY + "/"} if pending else {}
    source_before = {}
    before_hashes = {}
    def existing(relative):
        original = relative
        for canonical, legacy in aliases.items():
            if relative.startswith(canonical):
                original = legacy + relative[len(canonical):]
                break
        source_before[original] = file_hash(root / original)
        if original in predicted:
            content = base64.b64decode(predicted[original]["after"])
            before_hashes[relative] = digest(content)
            return content.decode()
        path = root / original
        # Text reads normalize CRLF for merging; approval binds the exact bytes
        # apply will inspect, including changes made only to line endings.
        before_hashes[relative] = source_before[original]
        return path.read_text() if path.is_file() else None
    baseline_text = existing(".plovi/local/setup-baseline.json")
    baseline = json.loads(baseline_text) if baseline_text is not None else {}
    current_text = existing(".plovi/project.json")
    current = json.loads(current_text) if current_text is not None else MISSING
    if current is MISSING:
        profile, conflicts = detected["profile"], []
    else:
        profile, conflicts = merge(baseline.get("profile", MISSING), current, detected["profile"], "/profile", answers.get("resolutions"))
    profile = overlay(profile, answers.get("profile", {}))
    selected = {row.get("id"): row.get("checkout_strategy") for row in
                answers.get("profile", {}).get("repositories", []) if "checkout_strategy" in row}
    for row in profile["repositories"]:
        if row["id"] in selected:
            row["checkout_strategy_explicit"] = selected[row["id"]] != "worktree"
    validate(profile, root)
    for repo in profile["repositories"]:
        child = contained(root, repo["path"])
        if child == root:
            continue
        child_config = configuration(child)
        if child_config.name == LEGACY and child_config.exists():
            ref = read_json(child_config / "project-ref.json", {})
            if not ref or (child / ref["root"]).resolve() != root:
                raise WorkflowError("Child legacy configuration does not reference this project; resolve its membership before setup")
            migration_roots.append(repo["path"])
            prefix = Path(repo["path"]).as_posix() + "/"
            aliases[prefix + CURRENT + "/"] = prefix + LEGACY + "/"
            source_before[prefix + LEGACY + "/project-ref.json"] = file_hash(child_config / "project-ref.json")
    files = generated(root, profile)
    # Native host discovery is installed only through an approved setup proposal.
    from .adapters import discovery_file, project_files
    files.update(project_files(root, profile))
    generation_base = dict(files)
    changes = []
    baseline_files = baseline.get("files", {})
    for relative, desired in files.items():
        destination = contained(root, relative, allow_root=False)
        old = existing(relative)
        if old is not None and relative not in baseline_files and discovery_file(relative) and old != desired:
            conflicts.append({"path": "/files/" + relative, "reason": "Existing unowned discovery entry; move it or select a different namespace"})
        if relative == "plovi.toml" and old is not None:
            desired = old
        elif relative == ".plovi/project.json" and current is not MISSING and profile == current:
            desired = old
        elif old is not None and relative in baseline_files and old != baseline_files[relative] and old != desired:
            normalized = old.replace("<!-- agentflow:start -->", BEGIN).replace("<!-- agentflow:end -->", END)
            if BEGIN in desired and BEGIN in normalized:
                old_block = normalized.split(BEGIN)[1].split(END)[0]
                base_text = baseline_files[relative].replace("<!-- agentflow:start -->", BEGIN).replace("<!-- agentflow:end -->", END)
                base_block = base_text.split(BEGIN)[1].split(END)[0] if BEGIN in base_text else None
                if old_block != base_block:
                    if answers.get("resolutions", {}).get("/files/" + relative) != "detected":
                        desired = normalized
            elif relative != ".plovi/project.json":
                desired = old
        files[relative] = desired
        if old != desired:
            changes.append({"path": relative, "before": before_hashes[relative], "content": desired,
                            "diff": "".join(difflib.unified_diff((old or "").splitlines(True), desired.splitlines(True), fromfile=relative, tofile=relative))})
    for relative, old_generated in baseline_files.items():
        if relative in files or not discovery_file(relative):
            continue
        destination = contained(root, relative, allow_root=False)
        if destination.is_file() and destination.read_text() == old_generated:
            changes.append({"path": relative, "before": file_hash(destination), "content": None,
                            "diff": "".join(difflib.unified_diff(old_generated.splitlines(True), [], fromfile=relative, tofile=relative))})
    proposal = {"schema_version": 1, "root": str(root), "profile": profile, "findings": detected["findings"],
                "questions": [] if answers.get("confirmed_defaults") or current is not MISSING else detected["questions"],
                "conflicts": conflicts, "changes": changes, "baseline": {"profile": detected["profile"], "files": generation_base},
                "baseline_before": before_hashes[".plovi/local/setup-baseline.json"]}
    if migration_roots:
        proposal["migration"] = {"notice": "Move .agentflow/ to .plovi/ on apply",
                                 "roots": migration_roots,
                                 "before": source_before | {relative: file_hash(root / relative) for relative in predicted}}
    proposal["approval"] = digest(json_text(proposal))
    return proposal

def apply(proposal: dict, approval: str) -> dict:
    payload = {k: v for k, v in proposal.items() if k != "approval"}
    if approval != proposal.get("approval") or approval != digest(json_text(payload)):
        raise WorkflowError("Approval must match this exact proposal digest")
    if proposal.get("questions") or proposal.get("conflicts"):
        raise WorkflowError("Resolve setup questions/conflicts and generate a new proposal first")
    root = Path(proposal["root"]).resolve()
    validate(proposal["profile"], root)
    if proposal.get("migration"):
        for relative, expected in proposal["migration"]["before"].items():
            if file_hash(contained(root, relative)) != expected:
                raise WorkflowError("Migration state changed since preview; generate a new proposal")
        from .migration import migrate
        for relative in proposal["migration"]["roots"]:
            migrate(contained(root, relative))
    baseline_path = root / ".plovi/local/setup-baseline.json"
    if file_hash(baseline_path) != proposal.get("baseline_before"):
        raise WorkflowError("Setup state changed since preview; generate a new proposal")
    paths = []
    for change in proposal["changes"]:
        path = contained(root, change["path"], allow_root=False)
        if file_hash(path) != change["before"]:
            raise WorkflowError(f"{change['path']} changed since preview; generate a new proposal")
        paths.append((path, change["content"]))
    backups = {p: p.read_bytes() if p.exists() else None for p, _ in paths}
    try:
        for path, content in paths:
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, content)
        text = json_text(proposal["baseline"])
        if not baseline_path.exists() or baseline_path.read_text() != text:
            atomic_write(baseline_path, text)
    except Exception:
        for path, old in backups.items():
            if old is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, old.decode())
        raise
    return {"root": str(root), "changed": [p.relative_to(root).as_posix() for p, _ in paths]}
