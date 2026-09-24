---
name: pr-preflight
description: Check a branch's readiness for a draft PR using scope, evidence, and delivery guards.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# pr preflight

1. Read the plan, base comparison, repository policies, and check evidence for the current revision.

2. Verify task scope, test/acceptance mapping, no unrelated staged changes, no credentials, and a valid feature branch/remote.

3. Inspect PR title/body against the final implementation and template. Flag unsupported testing claims and missing material limitations.

4. Run narrow missing checks when authorized, then report concrete blockers or readiness. A successful preflight does not itself push, create a PR, request reviews, or post comments.

