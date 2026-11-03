# Frozen project quality sources

Native user instructions take precedence over checkout defaults. These repository-relative sources are shared with every stage, including review. Read the full files at these paths; the excerpts below are the parts this task relies on.

## AGENTS.md

# plovi

This repository is a standalone public package. PLAN.md defines the approved scope.
Develop this package from this repository and its task worktrees; do not route package development through an installed personal workflow. New tasks use separate worktrees.
Keep skills generic and resolve project behavior from its profile and extensions.
Use Python 3.11+ and the standard library for installation and runtime.
Run: python3 -m unittest discover -s tests -v
Documentation: python3 -m mkdocs build --strict
Never modify real user agent configuration during tests. Use isolated child environments.
Keep private identifiers, real credentials, and machine-specific paths out of deliverables.
Commit logical changes locally. Publishing and remote changes require an explicit request.

<!-- plovi:start -->
Read PROJECT_WORKFLOW.md for this project's workflow defaults and custom skills.
Do not apply workflow defaults from an unrelated ancestor project.
<!-- plovi:end -->
Design: anything people see (app, docs site, brand) follows design/README.md and design/DESIGN.md; use only tokens from design/tokens.json.


New issues/tasks started through specify allocate their own branch and worktree
with task start before plan writes unless setup explicitly selected another strategy.
Manual execution does not waive the configured checkout policy.
Use returned checkout paths for every tool operation; never switch another chat's
shared checkout. Only explicit continuation may resume the same owned task.

## PROJECT_WORKFLOW.md

<!-- plovi:start -->
# Project workflow

- agent-workflow: .; library, docs; worktree; participate when-changed.

Plans: ai-plans/<task>/ inside the task worktree.
New tasks: task start before plan writes; distinct branch/worktree, including manual tasks.
Resume only the same owned task; do not reuse another chat's checkout.
Harnesses: Codex and Claude.
Execution: trusted. Tracker: github.
Project skills, rules, and connectors live under .plovi/.
Resolve this project's profile before using workflow defaults. Native instructions and explicit user requests take precedence.
<!-- plovi:end -->

Model selection uses project adaptive defaults in `.plovi/models.json` for new tasks.
Saved task routes remain frozen; both Codex and Claude are allowed.

## design/DESIGN.md (Voice)

## Voice

- Write the name in lowercase everywhere, including at the start of a sentence: "plovi opened PR #87".
- Name things by what people recognise: task, plan, review, pull request. Keep internal names (ledger, tick, slot) out of the app.
- Short, active sentences. A button says what happens ("Approve plan"); the toast repeats it ("Plan approved").
- Say who acts: "You merge." "plovi marks PRs ready when checks pass."
- Errors say what went wrong and the fix: "GitHub rejected the push: the branch needs a review. Ask a reviewer or switch autonomy to Mark ready."
- Real numbers: "2 tests failed", "3/4 running", "2h".
- No emoji, no exclamation marks, no "magic" or "seamless".
- Work that changes how people use plovi ends with a "What changes for your workflow" callout.

CLI text output, docs pages and skill text follow this voice. design/README.md and design/tokens.json apply to any visual docs change; this task adds no new visual tokens.

## Issue ground rules (MarkoArsov/agent-workflow#18)

- Runtime is Python 3.11+ standard library only. No new runtime dependencies.
- Works on macOS, Linux and Windows: pathlib, argv lists, `.cmd` launchers on Windows.
- Tests are part of the change. Use tests/helpers.py and tests/fixtures/provider_double.py. No network, no real agent CLIs, no real user configuration (isolated HOME, XDG_*, APPDATA). Never weaken, skip or delete an existing test.
- Before the PR: unittest discover, mkdocs build --strict, check_links site, generate_docs --check, check_public_content --history.
- No private identifiers, credentials or machine-specific paths in code, fixtures, docs or the PR.
- The PR body lists what changed, tests added (file and case names), commands run with results, and "What changes for your workflow".
