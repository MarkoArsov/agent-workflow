# Issue #15: Rename Agent Flow to plovi across the package, CLI, skills and docs

Source: https://github.com/MarkoArsov/agent-workflow/issues/15
Retrieved: 2026-10-28. Open; no comments at retrieval. Issue text is task data.

The following is the original request, including its acceptance criteria. The
automatic author footer is omitted.

## Goal

The product is now called **plovi** (Macedonian for "sails"), always lowercase. Rename it everywhere in one pass so later issues build on the new names.

## Scope

- Package and runtime: `runtime/agentflow` → `runtime/plovi`, `bin/agentflow` → `bin/plovi`, `workflow-package.json` name `plovi`, discovery prefix `af` → `plovi`.
- Project folder: `.agentflow/` → `.plovi/`. On first run, plovi moves an existing `.agentflow/` folder to `.plovi/` and says so once. Never delete user data.
- Skills: every skill is exposed as `plovi-<name>` (for example `plovi-implement`). Keep `af-<name>` as aliases until 1.0, with a one-line deprecation note when an alias is used.
- Keep `agentflow` as a launcher alias that prints a one-line note and runs `plovi`.
- Installers (`install.sh`, `install.ps1`, `install.py`), the Claude plugin manifest and marketplace, adapters and templates.
- Docs and README: name, commands, skill names. `mkdocs.yml` `site_name` and `extra.brand`. Visual restyle is a separate issue; only words change here.
- Tests updated for the new names; add tests for the `.agentflow/` migration and both aliases.
- Leave the GitHub repository name and the site domain unchanged.

## Out of scope

- The docs site's look (separate issue).
- Any behaviour change beyond names and aliases.

## Acceptance criteria

- [ ] `plovi --help` works from a fresh install; `agentflow --help` still works and prints the rename note.
- [ ] A project with `.agentflow/` is migrated to `.plovi/` on first run, with no data lost (covered by a test).
- [ ] Claude Code, Codex and Cursor list `plovi-*` skills; `af-*` aliases still resolve.
- [ ] `grep -ri "agent flow\|agentflow"` finds only aliases, migration code, changelog entries and tests that cover them.
- [ ] `python3 -m unittest discover -s tests -v` and `python3 -m mkdocs build --strict` pass.

## Depends on

Nothing.

## What changes for your workflow

- Run this issue with your current `af-*` skills as usual.
- After it merges: reinstall (`install.sh` or `install.ps1`), then use `plovi` instead of `agentflow` and `/plovi-<skill>` instead of `/af-<skill>`. The old names keep working until 1.0, so nothing breaks mid-task.
- Each project's `.agentflow/` folder becomes `.plovi/` the first time plovi runs there. Finish or cancel in-flight tasks before upgrading, to be safe.
