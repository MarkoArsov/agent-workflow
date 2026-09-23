---
name: worktree-remove
description: Remove explicitly selected clean task worktrees without deleting user work.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# worktree remove

1. List registered worktrees and resolve the user's exact target. Inspect status, untracked files, branch, and any active runner lock.

2. Do not remove a parked base checkout or a worktree used by a running task. Preserve plans and evidence unless their removal is separately requested.

3. Use git worktree remove only for an explicitly selected clean task worktree. A dirty target requires the user's concrete decision about preserving changes; never add --force to bypass it.

4. Verify registration removal. Branch deletion is a separate decision, not an automatic side effect.

