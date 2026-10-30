---
name: worktree-start
description: Prepare only the repositories selected for a task using their configured checkout strategies.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/plovi for commands.
<!-- resolver:end -->

# Prepare an isolated task checkout

A new task defaults to its own branch and worktree **before** plan writes. This
is independent of manual/full execution. Honor an explicit checkout choice made
during setup; unmarked legacy profiles retain isolated worktrees for new tasks. Do not alter old approved manifests or move
existing work merely to retrofit the rule.

1. Resolve the canonical project, a new task ID and explicit writable participants.
   Read-only companions need no branch. Select the configured base, or an explicitly
   requested dependency with --base. Never silently start from another task's HEAD.

2. Run `plovi --project <root> task start <task>`; add repeated --repository <id>
   when several writable repositories exist. This command creates owned worktrees
   for unmarked legacy profiles. Explicit setup choices use the selected checkout
   strategy; a shared checkout must be clean and unowned by another unfinished task.
   It never copies or stashes existing edits. Existing branches/paths are refused.

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
   their recorded execution behavior; shared checkouts require an explicit setup
   choice and cannot be taken over from an unfinished task. Do not create nested or duplicate worktrees on resume.

New setup profiles default to worktree; explicit setup choices are honored and
legacy approved plans retain their recorded checkout strategy. Missing planning.commit_plans means true.
