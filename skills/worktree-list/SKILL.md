---
name: worktree-list
description: Show registered project worktrees and their branch state.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# worktree list

1. Run worktrees for the active project. Relate each worktree to its registered repository and branch.

2. Inspect cleanliness only where needed to answer the request. Separate parked base checkouts from task worktrees.

3. Do not create, remove, switch, or prune anything during an inventory request.

