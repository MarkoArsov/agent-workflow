<!-- plovi:start -->
# Project workflow

- agent-workflow: .; library, docs; worktree; participate when-changed.

Plans: ai-plans/<task>/ inside the task worktree.
New tasks: task start before plan writes; distinct branch/worktree, including manual tasks.
Resume only the same owned task; do not reuse another chat's checkout.
Harnesses: Codex and Claude.
Execution: trusted. Tracker: github.
Project skills, rules, and connectors live under .plovi/.
Resolve this project's profile before using workflow defaults. Native instructions and explicit user requests take precedence.
<!-- plovi:end -->

Model selection uses project adaptive defaults in `.plovi/models.json` for new tasks.
Saved task routes remain frozen; both Codex and Claude are allowed.
