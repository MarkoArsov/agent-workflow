---
name: worktree-start
description: Prepare only the repositories selected for a task using their configured checkout strategies.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/plovi for commands.
<!-- resolver:end -->

# Prepare an isolated task checkout

A new task always needs its own branch and worktree **before** plan writes. This
is independent of manual/full execution and overrides the legacy current-checkout
shortcut for new specifications. Do not alter old approved manifests or move
existing work merely to retrofit the rule.

1. Resolve the canonical project, a new task ID and explicit writable participants.
   Read-only companions need no branch. Select the configured base, or an explicitly
   requested dependency with --base. Never silently start from another task's HEAD.

2. Run `plovi --project <root> task start <task>`; add repeated --repository <id>
   when several writable repositories exist. This command creates owned worktrees
   even for older profiles configured as current-checkout/feature-branch. It does
   not switch the shared checkout or write plans. It preserves source staged/dirty
   work instead of copying or stashing it. Existing branches/paths are refused.

3. Read configuration_root, checkouts, branches and plans from the result. Use those
   paths explicitly for all editing/tool operations and report them before plan
   writes. Branches alone do not isolate shared working files. Respect the configured
   multi-repository plan owner/shared store; never initialize a Git parent.

4. Only an explicit continuation of the same task may use `task start <task>
   --resume`, with the same repository/base selection. The receipt validates Git
   registration and branch ownership. Do not infer permission to resume from a
   name collision. Interrupted allocation retains owned progress; resume can finish
   it without deleting files or adopting unrelated work.

5. Put the returned branches in the full manifest and pass its canonical project
   root with --project at handoff. The runner reuses receipt-owned checkouts and
   rejects changed branches/membership. Legacy manifests without allocations keep
   their recorded execution behavior; that is not permission to start new work in
   a shared checkout. Do not create nested or duplicate worktrees on resume.
