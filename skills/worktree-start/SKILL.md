---
name: worktree-start
description: Prepare only the repositories selected for a task using their configured checkout strategies.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/plovi for commands.
<!-- resolver:end -->

# Prepare the task checkout

Use before specify writes plans, or when resuming a selected task. A complete
pipeline.json is optional at planning time; it is not needed to create the location
where that contract will be written.

1. Resolve the project, task ID, participating writable repositories, read-only
   companions, branch/base and checkout strategy from the user and profile. If a
   manifest exists, reuse its selection. Otherwise record these planning choices
   in the later plan. Do not create branches for unchanged/read-only companions.

2. Inspect status, staged edits, Git common directories, existing branches and
   registered worktrees. Reuse an unambiguous checkout already owned by this task.
   Never auto-stash/reset, move user edits, switch another task's shared checkout,
   or take over a branch in use elsewhere. Ask only for unresolved ownership/base
   or dirty-checkout decisions before any dependent switch.

3. Honor the configured strategy: current-checkout validates the existing branch;
   feature-branch creates/reuses the selected branch in its writable checkout;
   worktree creates/reuses the configured task worktree with that branch and base.
   Use the project's branch template and worktree directory. For concurrent work,
   separate worktrees isolate files; branches alone in one directory do not.

4. Verify project resolution, branch, repository/common directory and task paths
   before plan writes. Single-repository plans belong inside that task checkout's
   configured plan directory. Multi-repository plans use the configured plan-owning
   checkout or shared store; never initialize an unversioned parent or invent a
   repository to hold them. Report shared-location limitations explicitly.

5. Record the canonical configuration root as well as the chosen branches/paths.
   A single-repository worktree can contain a copied profile; pass the original
   configuration root explicitly with --project at runner handoff so its configured
   worktree directory is reused rather than nesting a second worktree. Execution must reuse that checkout;
   run the runner's preparation at pipeline handoff rather than creating a second
   worktree with a different identity. For manual work stay in the selected checkout.
   Report the resulting task paths and unchanged companions.


New setup profiles default writable participants to worktree. Explicit reviewed
feature-branch and current-checkout choices remain valid. Missing
planning.commit_plans means true; it never changes checkout strategy. Prepare
using the canonical configuration root and reuse existing registered task worktrees,
including ones with task-owned planning edits. Verify branch/common-dir ownership
before reuse. Keep read-only companions untouched.
