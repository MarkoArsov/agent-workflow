#!/usr/bin/env python3
"""Generate public references from an allowlist of package skills and schemas."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def rendered():
    skills = ["# Skill reference\n", "Standalone entry points use **aw-NAME**; Claude's native plugin uses **agent-workflow:NAME**.\n",
              "Project overrides take precedence in direct invocation and runner stages.\n"]
    for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
        if path.is_symlink():
            raise ValueError("Documentation sources must not be symlinks")
        text = path.read_text()
        header, body = text.split("---", 2)[1:]
        name = re.search(r"^name:\s*(.+)$", header, re.M)[1]
        description = re.search(r"^description:\s*(.+)$", header, re.M)[1]
        body = re.sub(r"<!-- resolver:start -->.*?<!-- resolver:end -->", "", body, flags=re.S).strip()
        body = re.sub(r"^# .+\n", "", body).strip()
        skills += [f"## {name}\n", description + "\n", body + "\n"]
    schemas = ["# Schema reference\n", "These schemas describe public configuration. Runtime validation also checks repository membership, dependencies, and executable evidence.\n"]
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        value = json.loads(path.read_text())
        schemas += [f"## {value['title']}\n", value.get("description", "") + "\n",
                    "| Field | Required | Format |\n|---|---|---|"]
        for name, prop in value.get("properties", {}).items():
            kind = ", ".join(map(str, prop["enum"])) if "enum" in prop else prop.get("type", "constant" if "const" in prop else "variant")
            schemas.append(f"| {name} | {'yes' if name in value.get('required', []) else 'no'} | {kind} |")
        schemas.append("")
    return {"skills.md": "\n".join(skills), "schemas.md": "\n".join(schemas)}

def generate(check=False):
    directory = ROOT / "docs/generated"
    if not check:
        directory.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, content in rendered().items():
        path = directory / name
        if not path.exists() or path.read_text() != content:
            stale.append(name)
            if not check:
                path.write_text(content)
    if check and stale:
        raise SystemExit("Stale generated references: " + ", ".join(stale))
    return stale

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    generate(parser.parse_args().check)
