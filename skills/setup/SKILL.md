---
name: setup
description: Set up Agent Flow for this project. Short name for project-setup.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agentflow for commands.
<!-- resolver:end -->

# setup

This is the short name for **project-setup**.

1. Find the project-setup skill. In a project that already has a profile, run the selected package's bin/agentflow skill resolve project-setup; it returns the project's override when one exists. Otherwise use project-setup/SKILL.md beside this skill's folder.
2. Read that file and follow its procedure exactly, including its approval steps.
3. Do not skip or shorten any step because this entry point has a shorter name.
