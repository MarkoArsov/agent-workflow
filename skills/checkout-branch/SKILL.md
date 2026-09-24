---
name: checkout-branch
description: Resolve and switch to an existing requested branch or its registered worktree.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# checkout branch

1. Resolve the requested branch from exact user input, issue metadata, or an existing PR. Do not derive an unrelated new slug.

2. Inspect project checkout strategy and existing worktrees. Prefer opening the branch's registered worktree where the project uses parked bases.

3. For a permitted feature checkout, ensure local edits are preserved before git switch. Do not stash, reset, or discard changes without instruction.

4. Verify the resulting branch and project membership. New branch creation belongs to specification/worktree preparation.

