---
description: Update, diagnose, or remove an existing Stagecoach installation.
---

# Update and remove

Project configuration and extensions belong to you.
Installed payloads live in separate versioned directories.

## Update

Use a reviewed release checkout or its pinned installer:

~~~sh
agent-workflow update --global --local-source /path/to/release --dry-run
agent-workflow update --global --local-source /path/to/release
~~~

For a project install, replace `--global` with `--target /path/to/project`.
The update stages and validates a payload before switching the active version.
Conflicts in modified installer-owned files are reported; partial failures restore previous files.

Project updates advance that project's package pin.
Global updates retain older versions so other projects can keep their pins.
Overrides are preserved, with changed upstream skill hashes reported for review.

## Diagnose

~~~sh
agent-workflow doctor --global
agent-workflow doctor --target /path/to/project
~~~

The report identifies installation ownership and modified owned files.
If a pinned version is missing, install that version or deliberately update the project.

## Remove

~~~sh
agent-workflow uninstall --global --dry-run
agent-workflow uninstall --global
~~~

Only unchanged receipt-owned files are removed.
Modified adapters/payloads and all project profiles, plans, skills, rules, and connectors remain.
Removing a project package allows fallback to a matching global package.

For native Claude ownership, use `--backend claude-plugin` with update/uninstall/doctor.
The runtime delegates to Claude's supported plugin CLI; it never edits its cache directly.
