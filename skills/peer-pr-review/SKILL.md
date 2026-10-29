---
name: peer-pr-review
description: Independently review another pull request and prepare actionable, unsent feedback.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/plovi for commands.
<!-- resolver:end -->

# peer pr review

1. Fetch PR metadata, the complete diff, and relevant repository context using read-only operations. Inspect base and head revisions.

Read the effective review skill and references/quality-guidance.md as read-only
method dependencies. Reuse its requirements -> behavioral tests -> correctness ->
conventions/semantic-duplication order and selected project guidance. Never inherit
pipeline review's permission to edit. Explain the PR's intent, project context and
solution in plain language before findings. Missing requirements are uncertainty,
not permission to guess.

2. Understand requirements and existing patterns before evaluating correctness, regressions, data/security boundaries, and test coverage.

3. Reproduce high-value concerns when feasible in an isolated checkout. Tie each finding to a concrete trigger and affected line.

4. Distinguish confirmed defects from uncertainty, and avoid cosmetic findings unless a project rule makes them consequential.

5. Prepare concise review comments and an overall assessment. Do not submit a review, comment, or change the author's branch unless explicitly requested.

