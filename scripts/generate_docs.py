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
    "Core workflow": ("setup", "specify", "implement-pipeline", "factory", "list-pipeline", "pipeline-workflow", "project-setup", "issue-writer", "draft-rfc"),
    "Implementation and verification": ("implement-tests", "implement", "review", "understand", "review-guide"),
    "Git and delivery": ("checkout-branch", "sync-base", "commit", "push", "commit-and-push", "draft-pr", "publish-workflow", "merge-to-base"),
    "Worktrees and environments": ("worktree-start", "worktree-list", "worktree-remove", "environment-status", "environment-release"),
    "Pull requests and design review": ("address-pr-comments", "diagnose-ci", "peer-pr-review", "peer-rfc-review", "request-review", "pr-preflight"),
    "End-to-end testing": ("e2e-test-overview", "e2e-test-engineering", "test-on-staging"),
    "Workflow maintenance": ("update-models", "add-rule", "prune-context", "project-customize", "wizard"),
}

# Intent → skills (validated to exist), optional CLI follow-up text, and an optional joiner.
FAST_LOOKUP = (
    ("Start a task", ("specify",), ""),
    ("Run a small follow-up or an isolated bugfix", ("specify", "implement"), ""),
    ("Revise an approved plan", ("specify",), "again, then `resume --rebind`"),
    ("Run the full pipeline", ("implement-pipeline",), ""),
    ("See what needs you", ("factory",), "or `inbox`"),
    ("See what is configured and running", ("list-pipeline",), "or `status`"),
    ("Respond to a paused task", ("implement-pipeline",), "or `answer TASK --file`"),
    ("Recheck after a fix", ("implement",), "or `verify PLAN --phase green`"),
    ("Publish task changes", ("commit-and-push",), ""),
    ("Publish workflow-package changes", ("publish-workflow",), ""),
    ("Refresh model and effort defaults", ("update-models",), ""),
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
    ("Set up a project", ("setup",), "(short for `project-setup`)"),
    ("Change the project workflow", ("project-setup", "project-customize"), "", " or "),
    ("Understand or change the workflow itself", ("pipeline-workflow",), ""),
)

def category_for(name):
    for category, names in SKILL_CATEGORIES.items():
        if name in names:
            return category
    return "Other"

def rendered():
    discovery = json.loads((ROOT / "workflow-package.json").read_text(encoding="utf-8")).get("discovery", {})
    prefix = discovery.get("prefix", "plovi")
    entries = []
    for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
        if path.is_symlink():
            raise ValueError("Documentation sources must not be symlinks")
        text = path.read_text(encoding="utf-8")
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
        f"!!! summary \"In one minute\"\n    - New project? Run `setup` first. Then `specify`, and `implement` for a small change or `implement-pipeline` for the full run.\n    - The other {len(entries) - 4} skills are for focused work, review, delivery, recovery, and maintenance.\n    - Standalone installs invoke **{prefix}-NAME**; the native Claude plugin uses **plovi:plovi-NAME**.\n    - Project overrides take precedence in direct invocation and in runner stages.\n",
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
        "---\ndescription: Public configuration schemas for plovi projects and task plans.\nfooter: reference\nfooter_order: 2\n---\n",
        "# Schema reference\n",
        "These schemas describe public configuration. Runtime validation also checks repository membership, dependencies, and executable evidence.\n",
    ]
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        schemas += [f"## {value['title']}\n", value.get("description", "") + "\n",
                    "| Field | Required | Format |\n|---|---|---|"]
        for name, prop in value.get("properties", {}).items():
            kind = ", ".join(map(str, prop["enum"])) if "enum" in prop else prop.get("type", "constant" if "const" in prop else "variant")
            schemas.append(f"| {name} | {'yes' if name in value.get('required', []) else 'no'} | {kind} |")
        schemas.append("")
    return {"skills.md": "\n".join(skills), "schemas.md": "\n".join(schemas)}


def commands_page():
    """docs/commands.md from the operations registry, the same data as `plovi commands --json`."""
    import sys
    sys.path.insert(0, str(ROOT / "runtime"))
    from plovi.operations import catalog
    rows = catalog()
    risk = {"none": "Reads only", "low": "Changes a task or the registry", "high": "Preview, then apply by digest"}
    lines = [
        "---\ntitle: Command reference\ndescription: Every plovi operation, its arguments, whether it changes anything and its risk.\nfooter: reference\nfooter_order: 3\n---\n",
        "# Command reference\n",
        "Generated from the operations registry by `scripts/generate_docs.py`. Agents read the same data with `plovi commands --json`.\n",
        "Every operation that changes something accepts `--reason`, `--actor-agent NAME` and `--via TOOL`, and records "
        "an event with that actor and reason in the [ledger](ledger.md). High-risk operations return a preview with a digest "
        "and change nothing until you pass `--approve DIGEST`.\n",
        "| Operation | Changes | Risk | What it does |", "|---|---|---|---|",
    ]
    lines += [f"| [`{row['name']}`](#{row['name'].replace('.', '')}) | {'yes' if row['mutates'] else 'no'} | {row['risk']} | {row['summary']} |"
              for row in rows]
    lines.append("")
    for row in rows:
        lines += [f"## {row['name']}\n", row["summary"] + ".\n", f"```sh\n{row['usage']}\n```\n",
                  f"Risk: **{row['risk']}**. {risk[row['risk']]}.\n"]
        properties = row["arguments"].get("properties", {})
        if properties:
            lines += ["| Argument | Required | Format | Meaning |", "|---|---|---|---|"]
            for name, prop in properties.items():
                kind = ", ".join(map(str, prop["enum"])) if "enum" in prop else prop.get("type", "value")
                lines.append(f"| `{name}` | {'yes' if name in row['arguments'].get('required', []) else 'no'} | {kind} | {prop.get('description', '')} |")
            lines.append("")
    lines += ["!!! note \"What changes for your workflow\"",
              "    Agents read `plovi commands --json` first and use these operations instead of editing plovi files.",
              "    People can use the same commands; `plovi inbox` names the one to run next.", ""]
    return "\n".join(lines)

def scenario_page():
    """docs/generated/scenario.md from tests/scenario/steps.py and owners.json."""
    import runpy
    steps = runpy.run_path(str(ROOT / "tests/scenario/steps.py"))
    rows, statuses = steps["SCENARIO_STEPS"], steps["load_owners"]()
    done = [row for row in rows if steps["status"](row, statuses) == "done"]
    lines = [
        "---\ntitle: Target scenario\ndescription: Every step of the target scenario, the issues that own it, its test and whether it works yet.\n"
        "question: How much of the target scenario works today?\n---\n",
        "# Target scenario\n",
        "Generated from `tests/scenario/steps.py` and `tests/scenario/owners.json` by `scripts/generate_docs.py`.\n",
        "!!! summary \"In one minute\"",
        "    - The target: tag issues, set a project up once, and let plovi plan, build and deliver them while you watch and steer.",
        f"    - {len(done)} of {len(rows)} steps are done: every owning issue has landed and the step's test runs in CI.",
        "    - A pending step's test is skipped with the issues it waits for. Each owning issue writes the test and marks itself done.",
        "    - [The stability gate](../stability-gate.md) counts these steps in G5.\n",
        "| ID | Step | Owners | Test | Status |", "|---|---|---|---|---|",
    ]
    for row in rows:
        test = f"`{steps['TEST_FILE']}` `{row['test']}`"
        if row.get("app_test"):
            test = f"Playwright `{row['app_test']}`, checked by {test}"
        owners = ", ".join(f"#{number}" for number in row["owners"])
        lines.append(f"| {row['id']} | {row['text']} | {owners} | {test} | {steps['status'](row, statuses)} |")
    lines += ["", "To own a step, see [Scenario tests: how to own a step](../development.md#scenario-tests-how-to-own-a-step).", ""]
    return "\n".join(lines)

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
    pages = {directory / name: content for name, content in rendered().items()}
    pages[ROOT / "docs/commands.md"] = commands_page()
    pages[directory / "scenario.md"] = scenario_page()
    for path, content in pages.items():
        name = path.relative_to(ROOT / "docs").as_posix()
        # Explicit UTF-8 and LF: Windows defaults to the ANSI code page and CRLF.
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(name)
            if not check:
                path.write_text(content, encoding="utf-8", newline="")
    if check and stale:
        raise SystemExit("Stale generated references: " + ", ".join(stale))
    return stale

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    generate(parser.parse_args().check)
