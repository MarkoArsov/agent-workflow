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
    "Core workflow": ("specify", "implement-pipeline", "list-pipeline", "pipeline-workflow", "project-setup", "issue-writer", "draft-rfc"),
    "Implementation and verification": ("implement-tests", "implement", "review", "understand", "review-guide"),
    "Git and delivery": ("checkout-branch", "sync-base", "commit", "push", "commit-and-push", "draft-pr", "merge-to-base"),
    "Worktrees and environments": ("worktree-start", "worktree-list", "worktree-remove", "environment-status", "environment-release"),
    "Pull requests and design review": ("address-pr-comments", "diagnose-ci", "peer-pr-review", "peer-rfc-review", "request-review", "pr-preflight"),
    "End-to-end testing": ("e2e-test-overview", "e2e-test-engineering", "test-on-staging"),
    "Workflow maintenance": ("add-rule", "prune-context", "project-customize", "wizard"),
}

# Intent → skills (validated to exist), optional CLI follow-up text, and an optional joiner.
FAST_LOOKUP = (
    ("Start a task", ("specify",), ""),
    ("Run a small follow-up or an isolated bugfix", ("specify", "implement"), ""),
    ("Revise an approved plan", ("specify",), "again, then `resume --rebind`"),
    ("Run the full pipeline", ("implement-pipeline",), ""),
    ("See what is configured and running", ("list-pipeline",), "or `status`"),
    ("Respond to a paused task", ("implement-pipeline",), "or `answer TASK --file`"),
    ("Recheck after a fix", ("implement",), "or `verify PLAN --phase green`"),
    ("Publish changes", ("commit-and-push",), ""),
    ("Open a draft pull request", ("draft-pr",), ""),
    ("Check a pull request before sending it", ("pr-preflight",), ""),
    ("Handle pull request feedback", ("address-pr-comments",), ""),
    ("Diagnose a failed CI run", ("diagnose-ci",), ""),
    ("Understand a change before reviewing it", ("understand",), ""),
    ("Guide a reviewer through a change", ("review-guide",), ""),
    ("Review someone else's pull request", ("peer-pr-review",), ""),
    ("Write an issue", ("issue-writer",), ""),
    ("Capture a recurring rule", ("add-rule",), ""),
    ("Trim instructions", ("prune-context",), ""),
    ("Set up or change the project workflow", ("project-setup", "project-customize"), "", " or "),
    ("Understand or change the workflow itself", ("pipeline-workflow",), ""),
)

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
    names = {name for name, _, _ in entries}
    missing = sorted({skill for _, used, *_ in FAST_LOOKUP for skill in used} - names)
    missing += sorted(set(sum(SKILL_CATEGORIES.values(), ())) - names)
    if missing:
        raise ValueError("Documentation references unknown skills: " + ", ".join(missing))
    lookup = ["| I want to… | Use |", "|---|---|"]
    for intent, used, extra, *joiner in FAST_LOOKUP:
        links = (joiner[0] if joiner else ", then ").join(f"[`{x}`](#{x})" for x in used)
        lookup.append(f"| {intent} | {links}{' ' + extra if extra else ''} |")
    skills = [
        "---\ntitle: Skills\ndescription: Find the right skill for the job, then browse every bundled skill.\nquestion: Which skill should I use?\nfooter: docs\nfooter_order: 5\n---\n",
        "# Skill reference\n",
        f"!!! summary \"In one minute\"\n    - Start with `specify`. Then `implement` for a small change, or `implement-pipeline` for the full run.\n    - The other {len(entries) - 3} skills are for focused work, review, delivery, recovery, and maintenance.\n    - Standalone installs invoke **aw-NAME**; the native Claude plugin uses **agent-workflow:NAME**.\n    - Project overrides take precedence in direct invocation and in runner stages.\n",
        "## Fast lookup\n",
        "\n".join(lookup) + "\n",
        "## All skills\n",
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
    import importlib.util
    spec = importlib.util.spec_from_file_location("workflow_docs_content", Path(__file__).with_name("docs_content.py"))
    content = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(content)
    content.validate()
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
