#!/usr/bin/env python3
"""Generate public references from an allowlist of package skills and schemas."""
from __future__ import annotations
import argparse
import html
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

SKILL_CATEGORIES = {
    "Plan & orient": ("specify", "draft-rfc", "issue-writer", "project-setup", "pipeline-workflow", "wizard", "understand"),
    "Build & test": ("implement-tests", "implement", "implement-pipeline", "e2e-test-engineering", "e2e-test-overview"),
    "Review & deliver": ("review", "review-guide", "peer-rfc-review", "peer-pr-review", "address-pr-comments", "request-review", "pr-preflight", "commit", "push", "commit-and-push", "draft-pr", "merge-to-base"),
    "Project operations": ("add-rule", "project-customize", "list-pipeline", "prune-context", "diagnose-ci"),
    "Worktrees & environments": ("checkout-branch", "worktree-start", "worktree-list", "worktree-remove", "sync-base", "environment-status", "environment-release", "test-on-staging"),
}

def category_for(name):
    for category, names in SKILL_CATEGORIES.items():
        if name in names:
            return category
    return "Other"

def rendered():
    entries = []
    for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
        if path.is_symlink():
            raise ValueError("Documentation sources must not be symlinks")
        text = path.read_text()
        header, body = text.split("---", 2)[1:]
        name = re.search(r"^name:\s*(.+)$", header, re.M)[1]
        description = re.search(r"^description:\s*(.+)$", header, re.M)[1]
        body = re.sub(r"<!-- resolver:start -->.*?<!-- resolver:end -->", "", body, flags=re.S).strip()
        body = re.sub(r"^# .+\n", "", body).strip()
        entries.append((name, description, body))
    grouped = {category: [] for category in SKILL_CATEGORIES}
    grouped["Other"] = []
    for entry in entries:
        grouped[category_for(entry[0])].append(entry)
    skills = [
        "---\ndescription: Browse project-owned skills and their checked responsibilities.\nfooter: docs\nfooter_order: 4\n---\n",
        "# Skill reference\n",
        "Standalone entry points use **aw-NAME**; Claude's native plugin uses **agent-workflow:NAME**. Project overrides take precedence in direct invocation and runner stages.\n",
        '<div class="skills-filter" data-skills-filter>\n<label for="skills-filter-input">Filter skills</label>\n<input id="skills-filter-input" type="search" placeholder="Try review, test, or worktree" autocomplete="off" data-skills-filter-input>\n<div class="skills-filter__index" aria-label="Skill index">\n',
    ]
    skills += [f'<a href="#{name}" data-skills-chip data-skill-chip-name="{name}">{name}</a>' for name, _, _ in entries]
    skills += ["\n</div>\n<p data-skills-empty hidden>No skills match that filter.</p>\n</div>\n"]
    for category, category_entries in grouped.items():
        if not category_entries:
            continue
        skills.append(f"## {category}\n")
        for name, description, body in category_entries:
            searchable = html.escape(f"{name} {description}", quote=True)
            skills += [f'### `{name}` {{ .skill-entry data-skill="{searchable}" }}\n', description + "\n", body + "\n"]
    schemas = [
        "---\ndescription: Public configuration schemas for Stagecoach projects and task plans.\nfooter: reference\nfooter_order: 2\n---\n",
        "# Schema reference\n",
        "These schemas describe public configuration. Runtime validation also checks repository membership, dependencies, and executable evidence.\n",
    ]
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
