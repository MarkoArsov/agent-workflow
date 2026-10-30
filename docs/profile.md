---
title: Profile reference
description: Reference the project profile that records workflow configuration.
footer: reference
footer_order: 1
question: What does the project profile contain?
---

# Profile reference

!!! summary "In one minute"
    - `.plovi/project.json` is the authoritative configuration; `PROJECT_WORKFLOW.md` summarizes it.
    - It records repositories, agents, planning locations, Git conventions, delivery, tracking, execution, routes, extensions, and environments.
    - Unknown extension keys are preserved across re-setup.
    - Change it through setup, and inspect the resolved result with `plovi inspect`.

The authoritative file is `.plovi/project.json`.
PROJECT_WORKFLOW.md is the concise human-readable summary; setup updates its managed block while preserving your surrounding prose.

| Field | Meaning |
|---|---|
| schema_version | Supported format version, currently 1. |
| project | Stable ID and single-repo or multi-repo kind. |
| package.version | Pinned package version for this project. |
| repositories | IDs, relative paths, roles, base branches, remotes, participation, checkout strategies, commands. |
| agents | Enabled claude, codex, and/or cursor. |
| planning | Plan directory, ignored evidence directory and `commit_plans` (boolean, default true). |
| git | Branch/commit conventions and worktree directory. |
| delivery | Project delivery defaults; the task still selects actions. |
| tracking | none, github, linear, notion, or custom. |
| execution | Permission mode and provider-specific settings. |
| pipeline | Default stages and explicit provider routes. |
| extensions | Project-relative skill, rule, reference, connector, and stage locations. |
| environments | Optional owned local services, readiness patterns, exports, and shared lock IDs. |

Unknown extension keys are preserved. Repository and command collections use stable IDs/keys during re-setup.

Use `plovi inspect` to see the resolved profile and effective skill origins.
Use setup for reviewable configuration changes; do not edit installed defaults.

[Schema reference](generated/schemas.md) · [Project layout](projects.md)

New writable repositories default to `checkout_strategy: worktree`. Setup can
review an explicit `feature-branch` or `current-checkout` choice for new tasks.
Unmarked legacy profiles continue to allocate an owned worktree.
Re-setup preserves explicit choices. Missing legacy `planning.commit_plans` means
true; native instructions and explicit user decisions retain precedence. Existing
saved run bindings are not rewritten by this profile default.

!!! note "What changes for your workflow"
    Each task gets its own branch and worktree by default. Specify commits the
    complete planning contract there before asking for implementation approval.
    Setup can explicitly disable plan commits or select another checkout strategy.
