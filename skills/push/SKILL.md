---
name: push
description: Push an explicitly selected verified feature branch using a normal Git push.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# push

1. Confirm repository, remote, branch, and upstream. Inspect commits to be pushed and their verification evidence.

2. Reject a base branch, detached HEAD, or unexpected target. Never force-push or use force-with-lease.

3. Push the exact feature branch normally. On rejection, inspect divergence and ask for a concrete resolution only when necessary; do not overwrite remote work.

4. Report the pushed revision. PR creation, ready state, comments, and tracker updates are separate actions.

