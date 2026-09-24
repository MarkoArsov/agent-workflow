---
title: Skills and stages
description: Create project-owned skill overrides, skills, and custom stages.
question: How do I change a skill or add a stage for one project?
---

# Skills and stages

!!! summary "In one minute"
    - `skill copy` makes a project-owned override of a bundled skill; `skill new` adds your own.
    - Overrides record the upstream version they came from, and updates report upstream changes without overwriting yours.
    - Custom stages declare a skill or a command, inputs, outputs, completion checks, and a position before or after a named stage.
    - Each run snapshots the effective configuration, so changes apply to the next run or a reviewed rebind.

Each project can change its workflow without affecting another project.

## Change a skill

~~~sh
agent-workflow skill copy review
~~~

Edit the returned project-owned SKILL.md. The override records its upstream base hash.
Updates report changed upstream guidance while preserving your copy.

## Add a skill

~~~sh
agent-workflow skill new release-notes --description "Draft release notes from verified changes."
~~~

Replace the scaffold with a complete procedure, clear trigger, and any supporting resources.
Then run `agent-workflow refresh` to preview discovery changes.
Save and approve the proposal through the same setup apply command.

Use `skill list` or `skill resolve NAME` to confirm the effective source.
Direct invocation and runner stages use that same source.

## Add a stage

A custom stage extends the ordered pipeline:

~~~json
[
  {
    "id": "release-notes",
    "skill": "release-notes",
    "after": "review",
    "inputs": [{"repository": "app", "path": "README.md"}],
    "outputs": [{"repository": "app", "path": "CHANGELOG.md"}],
    "checks": ["docs"]
  }
]
~~~

Store it at `.agent-workflow/stages.json`. Add the stage and its named check to the task manifest.
Use exactly one skill or command, plus exactly one before or after dependency.
Outputs must also fit the task's writable scope. Custom stages cannot follow publication.

The runner verifies required artifacts and completion checks.
Changes invalidate earlier green evidence; delivery requires checks against the final diff.

## Share your configuration

Commit profiles, extensions, portable child references, and plans as appropriate.
Keep runtime payloads, evidence, machine-specific registrations, credentials, and local baselines ignored.

A run snapshots effective configuration and skill resources.
Package or extension changes affect the next run; a reviewed `resume --rebind` records changed inputs and invalidates affected stages.

<!-- checkpoints: CTX-5, ORG-5 -->
