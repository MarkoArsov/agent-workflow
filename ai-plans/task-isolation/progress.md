# Task isolation correction

The user explicitly requested enforcement and an audit after observing concurrent
work on one checkout. This is a correction to the completed workflow change, not
an invocation of specify; implementation is authorized directly. The earlier
manual/Codex-only choice remains. No independent agents are started.

Audit: two local chats pointed to the same primary checkout and task branch. Both
workflow improvements and rename/CI fixes were already committed together on PR #39.
The working tree was clean. This correction was moved into a new managed worktree
and branch before product edits; the other chat and published history are preserved.
An old prunable detached temporary-worktree registration was left untouched.

Regression: the task-start CLI invocation failed an assertion before implementation
because the command was absent. Seven isolated tests now prove separate allocations,
manual/legacy-profile isolation, dirty/staged source preservation, explicit owned
resume, collision refusal, selected bases, same-checkout runner handoff and partial
multi-repository recovery. Fixtures use isolated homes and fictional Git identity.

The new CLI creates no plan/product files, performs no fetch or model call, and
never switches the shared source branch. All subsequent agent operations must use
its returned paths. This is checkout/runner ownership enforcement, not an operating-
system restriction on arbitrary tools. Existing unallocated manifests retain their
legacy execution behavior, while new specifications must use task start.


Verification: all 185 isolated tests passed in 85.429 seconds, including seven task
ownership fixtures and the existing runner/legacy-manifest cases. Strict MkDocs
build and 3,968 internal links/assets passed; generated docs/wrappers and source/site
rename audits passed. Source/history generic content audit had zero findings without
an external private denylist. The original shared checkout remained clean at its
audit revision and stayed on its existing branch. This chat is now attached to the
new managed worktree; the other chat remains in the original checkout. Prior shared
commits were not moved or rewritten. The enforcement change needs merge/update
before an installed copy pointing at the original checkout loads the new rule.
