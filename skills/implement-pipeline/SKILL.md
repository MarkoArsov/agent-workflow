---
name: implement-pipeline
description: Preflight, start, observe, and recover a fresh-session implementation pipeline from an approved plan.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# implement pipeline

1. Resolve the configured project and locate the complete pipeline.json. Read the plan and confirm there are no unresolved product choices or unapproved delivery actions.

2. Run validate-plan and preflight. Address missing routes, binaries, connector availability, verification contracts, and checkout mismatches before launch. Never silently change trusted/restricted settings.

3. Use run with --dry-run to show the resolved stages and scope. Start run or run --detach when the user asks for the full pipeline. Detached output includes the task ID and log.

4. Observe status or bounded watch. The runner owns one project lock, fresh stage sessions, verification, and delivery. Do not start competing agents against its files.

5. For needs_input, show the exact saved question. Write the user's answer to a local file and use answer --file; this resumes the asking session. Do not answer on the user's behalf.

6. For failure, inspect the recorded attempt/evidence and repair the concrete cause. Use resume for an unchanged contract; use resume --rebind for a reviewed complete revision.

7. Use cancel to request termination of owned child processes. Never kill a process merely because a stale journal contains its PID.

8. Report final stage state, checks, participating repositories, and any partial delivery. Unknown token usage/cost remains unknown.

