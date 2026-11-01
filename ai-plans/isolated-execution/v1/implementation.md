# Implementation approach

Base bd6b824 includes #16 policy.py, claims.py, task and repo-ops locks, delivery
intent reconciliation and CLI unattended handling. Read these interfaces again
before edits; preserve their tests and recovery semantics.

1. Author independent behavioral tests first in the two new suites. Red checks
exercise existing public entry points where possible (unattended run and policy
validation). Guard new APIs with assertion-level capability checks. Do not alter
product sources to obtain red. Green-only suites cover remaining matrix cases.
2. Add factory.py for paths, remote identity registry, locks, independent mirrors,
refspec migration, ownership receipts and terminal cleanup. Reuse util.user_data,
identifier validation and state.lock; establish shared user-data locks to cover
multiple project roots with the same ID. Atomic origin.json compares all selected
repository URLs and refuses incompatible registration. Host credentials stay on host.
3. Integrate strategy resolution once before claims/preflight/prepare; persist it
and pass the same checkout map through snapshot, prompt, environment and delivery.
Update tasks.py/project.py membership validation for factory receipt ownership.
Factory claims use the logical repository identity plus separate checkouts and
existing path-overlap rules, never infer safety solely from different disk paths.
Snapshots omit parked user clones only for validated factory allocations. Preserve
read-only companions in guard snapshots. Refresh only remote-tracking refs, leaving
task branch and worktree administrative refs intact. Push explicit effective URLs.
4. Extend policy/schema/setup and add isolation.py: typed validation, runtime/image
probe, container_argv builder and process wrapper. No broad host subprocess
interception: thread an explicit execution context through runner, verification,
verify CLI, custom stages and environments. Preflight runs selected harness help
inside the image. All wrapper output is fed back into existing process/evidence
parsers. Stop/remove containers by saved owned names even when the client dies.
5. Mount mirrors read-only at their real paths so worktree .git pointers resolve.
Git optional locks are disabled inside containers. Verify image Git ownership and
safe.directory behavior using exact task paths only. Multi-repository prompts
receive the complete task map. Never grant the entire user-data tree as a mount.
Environment lease services need shared task network ownership, not host execution.
6. Add worktrees/clean CLI and update docs, Dockerfile and generated sources. Keep
build output untracked. Run the matrix in pipeline.json, review requirements then
tests then implementation/failure paths and design conventions. Make logical local
commits; stop before any remote effect.

## Current-checkout handoff constraint

The user explicitly requires this checkout for package development. This full
contract stays on codex/isolated-execution here. The existing automated runner's
profile still says worktree and would allocate a second checkout; do not launch it
against this branch as-is. After approval, execute the named stages directly in
this checkout, preserving independent review, or obtain an explicit user choice to
use task-start allocation. Full lane describes contract/stage order, not permission
to ignore the checkout constraint. No project profile or ownership receipt is changed
merely to make preflight appear to promise same-checkout pipeline execution.

## Reviewed technical sources

- https://git-scm.com/docs/git-clone (--mirror ref mapping differs from normal clone).
- https://docs.docker.com/reference/cli/docker/container/run/ (mounts, env, pull policy).
- https://docs.podman.io/en/latest/markdown/podman-run.1.html (runtime flags/rootless mapping).
These inform the proposed design; fake-runtime tests alone cannot prove containment.
