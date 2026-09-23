"""Resolve user-owned extensions without editing installed defaults."""
from __future__ import annotations
import re
import shutil
from pathlib import Path
from .util import WorkflowError, contained, digest, identifier, package_root, read_json, write_json

def metadata(path: Path) -> dict:
    text = path.read_text()
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise WorkflowError(f"Skill needs YAML frontmatter: {path}")
    header = text.split("---", 2)[1]
    name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", header, re.M)
    description = re.search(r"^description:\s*(.+)$", header, re.M)
    if not name or not description:
        raise WorkflowError(f"Skill needs name and description: {path}")
    if name[1] != path.parent.name:
        raise WorkflowError(f"Skill folder/name mismatch: {path}")
    return {"name": name[1], "description": description[1].strip().strip("'\"")}

def catalog(project=None, package=None) -> dict:
    package = Path(package) if package else package_root()
    result = {}
    roots = [(package / "skills", "package")]
    if project:
        roots.append((contained(project.root, project.profile["extensions"]["skills"]), "project"))
    for root, origin in roots:
        for path in sorted(root.glob("*/SKILL.md")):
            info = metadata(path)
            result[info["name"]] = info | {"path": str(path), "origin": origin, "sha256": digest(path.read_bytes())}
    return result

def resolve_skill(name: str, project=None, package=None) -> Path:
    identifier(name)
    skills = catalog(project, package)
    if name not in skills:
        raise WorkflowError(f"Unknown skill {name}; add it and run refresh")
    return Path(skills[name]["path"])

def copy_skill(project, name: str, package=None) -> Path:
    source = (Path(package) if package else package_root()) / "skills" / identifier(name)
    if not (source / "SKILL.md").is_file():
        raise WorkflowError(f"No bundled skill named {name}")
    destination = contained(project.root, project.profile["extensions"]["skills"]) / name
    if destination.exists():
        raise WorkflowError("A project override already exists; edit it directly")
    shutil.copytree(source, destination)
    # Bundled resolver bootstraps are package-owned, not portable override assets.
    resolver = destination / "scripts/resolve.py"
    resolver.unlink(missing_ok=True)
    path = destination / "SKILL.md"
    text = path.read_text()
    text = re.sub(r"<!-- resolver:start -->.*?<!-- resolver:end -->\n*", "", text, flags=re.S)
    path.write_text(text)
    lock = read_json(project.config / "overrides.lock.json", {})
    lock[name] = {"version": project.profile["package"]["version"], "sha256": digest((source / "SKILL.md").read_bytes())}
    write_json(project.config / "overrides.lock.json", lock)
    return path

def new_skill(project, name: str, description: str) -> Path:
    identifier(name)
    if not re.fullmatch("[a-z0-9-]+", name) or "\n" in description:
        raise WorkflowError("Use a hyphenated skill name and one-line description")
    path = contained(project.root, project.profile["extensions"]["skills"]) / name / "SKILL.md"
    if path.exists():
        raise WorkflowError("Skill already exists")
    path.parent.mkdir(parents=True)
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n\n# {name.replace('-', ' ').title()}\n\nDescribe the intended outcome and project-specific procedure here.\n")
    return path

def snapshot(project, package=None) -> dict:
    result = {"profile": project.profile, "skills": {}}
    for name, info in catalog(project, package).items():
        folder = Path(info["path"]).parent
        assets = {str(p.relative_to(folder)): {"sha256": digest(p.read_bytes()), "content": p.read_text(errors="replace")}
                  for p in sorted(folder.rglob("*")) if p.is_file() and not p.is_symlink() and p.name != "SKILL.md" and "__pycache__" not in p.parts}
        result["skills"][name] = {"origin": info["origin"], "content": Path(info["path"]).read_text(), "assets": assets}
    for key in ("rules", "references", "connectors"):
        directory = contained(project.root, project.profile["extensions"][key])
        result[key] = {str(p.relative_to(directory)): p.read_text() for p in sorted(directory.rglob("*")) if p.is_file() and not p.is_symlink()}
    result["stages"] = read_json(contained(project.root, project.profile["extensions"]["stages"]), [])
    return result
