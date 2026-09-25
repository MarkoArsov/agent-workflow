---
name: worktree-start
description: Prepare only the repositories selected for a task using their configured checkout strategies.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# worktree start

1. Read the task manifest and project repository policies. Explicitly distinguish read-only companions from writable participants.

2. Check for existing user changes and worktree registrations. Do not move parked base checkouts onto task branches.

3. Use the runner's preparation when launching a pipeline. For a manual task, use Git worktree add at the configured worktree directory with the approved branch/base; reuse a matching existing worktree.

4. A feature-branch strategy deliberately switches only its selected writable checkout. Current-checkout means validate the existing branch.

5. Verify branch, common Git directory, and project resolution inside each task checkout. Report exact paths and unchanged companion repositories.

