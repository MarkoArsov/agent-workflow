---
title: Update and remove
description: Update, diagnose, or remove an existing Agent Flow installation.
question: How do I update, diagnose, or remove an installation?
---

# Update and remove

!!! summary "In one minute"
    - Updates stage and validate a new payload before switching, and roll back on failure.
    - Your project skills, rules, and connectors are preserved; a project update only advances the profile's package pin.
    - Uninstall removes only unchanged files the installer owns.
    - The native Claude plugin is managed through Claude's own plugin commands.

Project configuration and extensions belong to you.
Installed payloads live in separate versioned directories.

## Update

Run the install command again. It installs the newest release beside the current one and switches to it; your projects' skills, rules, and connectors stay as they are.

~~~sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh
~~~

To update from a reviewed checkout instead:

~~~sh
agentflow update --global --local-source /path/to/release --dry-run
agentflow update --global --local-source /path/to/release
~~~

For a project install, replace `--global` with `--target /path/to/project`.
The update stages and validates a payload before switching the active version.
Conflicts in modified installer-owned files are reported; partial failures restore previous files.

Project updates advance that project's package pin.
Global updates retain older versions so other projects can keep their pins.
Overrides are preserved, with changed upstream skill hashes reported for review.

## Diagnose

~~~sh
agentflow doctor --global
agentflow doctor --target /path/to/project
~~~

The report identifies installation ownership and modified owned files.
If a pinned version is missing, install that version or deliberately update the project.

## Remove

~~~sh
agentflow uninstall --global --dry-run
agentflow uninstall --global
~~~

Only unchanged receipt-owned files are removed.
Modified adapters/payloads and all project profiles, plans, skills, rules, and connectors remain.
Removing a project package allows fallback to a matching global package.

For native Claude ownership, use `--backend claude-plugin` with update/uninstall/doctor.
The runtime delegates to Claude's supported plugin CLI; it never edits its cache directly.
