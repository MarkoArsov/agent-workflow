---
name: issue-writer
description: Draft a concise actionable issue from a problem or feature request.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# issue writer

1. Resolve the selected tracker or use Markdown when none is configured. Read the user's evidence and relevant project context.

2. Write a clear title, concrete problem/outcome, scope boundaries, and testable acceptance criteria. Include only links that help implement or assess the change.

3. Separate facts from assumptions and avoid inventing priorities, assignees, estimates, or team identifiers.

4. Show the complete draft. Issue creation or updates require explicit authorization for that action/content through an available connector.

5. Keep a local Markdown path when tracker access is unavailable; do not pretend the issue was created.

