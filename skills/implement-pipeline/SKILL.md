---
name: implement-pipeline
description: Preflight, start, observe, and recover a fresh-session implementation pipeline from an approved plan.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/plovi for commands.
<!-- resolver:end -->

# implement pipeline

Full planning is the default for substantive work, but explicit manual tasks use
implement in session instead. A prose plan or draft with unresolved routes is not
an execution-ready contract. Do not silently generate missing approval or change
lanes to get past preflight. Reuse the branch/worktree chosen during specification, passing its recorded canonical
configuration root with --project so a copied profile cannot cause nested worktrees.

1. Resolve the configured project and locate the complete pipeline.json. Read the plan and confirm there are no unresolved product choices or unapproved delivery actions.

2. Run validate-plan and preflight. Address missing routes, binaries, connector availability, verification contracts, and checkout mismatches before launch. Never silently change trusted/restricted settings. For GitHub delivery, verify that the launching environment resolves the intended `gh` executable and account-routing configuration; do not switch the global active account.

3. Use run with --dry-run to show the resolved stages and scope. Start run or run --detach when the user asks for the full pipeline. Detached output includes the task ID and log.

4. Observe status or bounded watch. The orchestrator owns one project lock, fresh stage sessions, verification, and delivery. Do not start competing agents against its files.

5. For needs_input, show the exact saved question. Write the user's answer to a local file and use answer --file; this resumes the asking session. Do not answer on the user's behalf.

6. For failure, inspect the recorded attempt/evidence and repair the concrete cause. Use resume for an unchanged contract; use resume --rebind for a reviewed complete revision.

7. Use cancel to request termination of owned child processes. Never kill a process merely because a stale journal contains its PID.

8. Report final stage state, checks, participating repositories, and any partial delivery. Unknown token usage/cost remains unknown.



Read policy show and preflight's permission mode/source. Detached/non-TTY runs are
restricted by default; do not silently add --trusted. Report escalated with its
kind/reason and retry command. Retry starts fresh with a person-provided note;
answer retains the exact asking session. Resume cannot clear escalations or pending
size/protected-path approvals. Show the diff and request each exact pending gate.
Task locks and repository claims permit disjoint worktree tasks to overlap; use
--no-wait only when an immediate claim conflict is desired. Interrupted recovery
verifies retained output and reconciles delivery; never duplicate completed work.

New specifications must use task start and the returned owned paths. Manual lane
selection does not change the configured checkout policy. Resume only this task's allocation;
never use a name collision to take over a different chat's branch or checkout.
