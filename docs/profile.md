---
title: Profile reference
description: Reference the project profile that records workflow configuration.
footer: reference
footer_order: 1
question: What does the project profile contain?
---

# Profile reference

!!! summary "In one minute"
    - `.stageway/project.json` is the authoritative configuration; `PROJECT_WORKFLOW.md` summarizes it.
    - It records repositories, agents, planning locations, Git conventions, delivery, tracking, execution, routes, extensions, and environments.
    - Unknown extension keys are preserved across re-setup.
    - Change it through setup, and inspect the resolved result with `stageway inspect`.

The authoritative file is `.stageway/project.json`.
PROJECT_WORKFLOW.md is the concise human-readable summary; setup updates its managed block while preserving your surrounding prose.

| Field | Meaning |
|---|---|
| schema_version | Supported format version, currently 1. |
| project | Stable ID and single-repo or multi-repo kind. |
| package.version | Pinned package version for this project. |
| repositories | IDs, relative paths, roles, base branches, remotes, participation, checkout strategies, commands. |
| agents | Enabled claude, codex, and/or cursor. |
| planning | Plan directory and ignored evidence directory. |
| git | Branch/commit conventions and worktree directory. |
| delivery | Project delivery defaults; the task still selects actions. |
| tracking | none, github, linear, notion, or custom. |
| execution | Permission mode and provider-specific settings. |
| pipeline | Default stages and explicit provider routes. |
| extensions | Project-relative skill, rule, reference, connector, and stage locations. |
| environments | Optional owned local services, readiness patterns, exports, and shared lock IDs. |

Unknown extension keys are preserved. Repository and command collections use stable IDs/keys during re-setup.

Use `stageway inspect` to see the resolved profile and effective skill origins.
Use setup for reviewable configuration changes; do not edit installed defaults.

[Schema reference](generated/schemas.md) · [Project layout](projects.md)
