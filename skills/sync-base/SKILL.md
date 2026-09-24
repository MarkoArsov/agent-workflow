---
name: sync-base
description: Fast-forward selected clean base checkouts without merging task branches.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# sync base

1. Resolve the explicitly requested repositories, their base branches, and remotes. Inspect cleanliness and current branch.

2. Use sync-base with the selected repository IDs. It fetches and fast-forwards only a clean checkout already on its configured base.

3. If local commits diverge, report the divergence and stop that repository's sync. Do not reset, force-push, or invent a merge.

4. Do not synchronize unrelated repositories or switch a task worktree to base.

