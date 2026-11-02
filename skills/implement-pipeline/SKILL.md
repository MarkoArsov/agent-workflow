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

3. Use run with --dry-run to show the resolved stages and scope. Use pipeline MANIFEST for a new approved task, or pipeline TASK for its continuation. This entry point pins the runtime outside mutable source, reuses an active worker, and performs safe resume/recovery before new inference. Pass the canonical --project root and preserve reviewed permission settings. Pending decisions, escalation, explicit cancellation and approvals remain visible stops. Do not retry or answer them on the person's behalf.

4. Attach tracking from the foreground host using the returned descriptor's argv/cwd and the selected execution.tracking_mode. In a terminal, pipeline detaches the worker and follows watch automatically. In Codex, Claude/VS Code or Cursor, inspect the actual available host tools: use open_and_run only with a verified session/running acknowledgement; open_only opens the panel and provides the exact command, without claiming it is running. Reuse a verified task/run terminal; probe a saved handle before reusing it and do not open duplicate panels if liveness is unknown. Unsupported/headless hosts get the safe command. Never use keyboard automation, invent a terminal API, or open UI from detached stages. Viewer failure/closure leaves the worker running. Human status/watch is concise; use --json for summary/event records and --verbose deliberately for full status. Do not start competing agents against the task's files.

5. For needs_input, show the exact saved question. Write the user's answer to a local file and use answer --file; this resumes the asking session. Do not answer on the user's behalf.

6. For an interruption, pipeline TASK revalidates retained output and continues without repeating successful inference. For failure, inspect saved attempts/checks and repair the cause. Mechanical fixture defects use the bounded independent test-author/reviewer path; implementation must never unfreeze tests directly. Use --rebind only for a reviewed complete revision. Missing or tampered pinned runtimes require restoration or an explicit --upgrade-runtime --rebind; changing the linked package does not upgrade an active task.

7. Use cancel to request termination of owned child processes. Never kill a process merely because a stale journal contains its PID.

8. Report final stage state, checks, participating repositories, and any partial delivery. Unknown token usage/cost remains unknown.



Launching with pipeline (or run, resume, answer, retry and approve) records the
plan approval for the current plan hash, with the launching actor. Background
workers refuse a plan whose current hash has no recorded approval, or a run whose
plan changed since it started; the error names `plovi approve TASK --plan`. Show the
person that preview and apply its hash only on their explicit approval. Agents pass
`--actor-agent NAME --via TOOL --reason TEXT` on every changing command, and preview
high-risk approvals before applying them by digest. Use `plovi inbox` to list what
waits on the person, and `pause`/`resume` to stop at a stage boundary and continue.

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

For an existing stopped task, use pipeline TASK with its saved task allocation.
An explicitly cancelled task requires the person to request continuation via resume;
pipeline TASK preserves the cancellation. Resume replays retained successful output through checks
before asking a provider to repeat work. A reviewed plan revision uses --rebind;
repository IDs/access/branches must remain unchanged. Only exact repair hashes in
recovery.approved_commits may advance a baseline, plus task-plan-only follow-up
commits during reviewed rebind. Unknown or dirty repairs stop for inspection.
Report recovered checks and stages separately from new provider work. Use the
launcher containing the approved fixes and verify the configured account first.

For a legacy run with a completed test stage and changed runtime instructions,
preview migrate TASK before a rebind that would discard that stage. A reviewed
recovery.test_checkpoint must match the saved binding and exact fixture escalation.
Keep requirements, old checks/outcomes/routes and all frozen hashes unchanged.
Approve exact source commits (and merges separately); never infer authorization
from a path whitelist. Add fixture-health checks when needed and use the bounded
independent repair request. Apply migration only within existing user approval.
It renews setup/red proof, preserves test authoring, and leaves implementation
stopped. Continue with pipeline TASK only when implementation is requested. Do not
hand-edit saved state or regenerate completed tests to bypass migration failures.

New unattended tasks use factory allocations from the remote base; report the
returned task map and preserve the user's source clone. Resume uses saved owned
checkouts and never relocates existing work. Container policy requires factory
receipts and a pinned local image; report degraded restricted fallback explicitly.
Contain agent/custom/check/service execution, while the host owns guards and
all delivery. Stop/remove only receipt-owned containers during locked recovery.
