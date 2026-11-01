# Implementation and rollout

Recommend the core reliability slice before resuming #17. Keep #17 stopped while
this plan is reviewed and implemented. Do not intertwine runtime upgrades with a
running stage. Native terminal convenience follows capability validation and must
not delay safe CLI tracking or #17 restart when an app lacks a supported API.

The current planning branch is stacked on the committed repair baseline 5b2d2c3;
it contains no uncommitted #17 stage output. Before delivery, isolate the reliability
changes/needed repair commits into a clean main-targeted change and exclude unrelated
#17 plans. This extraction must preserve both task histories and never rewrite a
published branch. The later user instruction authorizes manual implementation, local commits, normal push and a draft PR. No merge or publication is selected.

1. Freeze regression scenarios and author independent tests. Reproduce watch state
   dumping/idle ambiguity and fixture-failure escalation with existing public APIs,
   using assertion failures rather than missing imports as red evidence.
2. Build explicit failure/action types, event schema and small live summary. Keep
   runner transition logic separate from presentation, provider parsing and host UI.
   Centralize bounded retry/repair accounting and journal intent before effects.
3. Implement the independent fixture-repair subworkflow, setup checks, review and
   test revision fingerprints. The saved implementation output remains untouched
   until repair validation; no review model can silently change approved behavior.
4. Harden artifact recovery and runtime pinning, preserving existing account and
   delivery controls. Implement state migration/rollback and stable launcher routing.
5. Implement cursor-based watch/status, heartbeat/liveness and owned cancellation.
   Use deterministic clocks to test races, stale output and orphan detection.
6. Add a generic tracking descriptor and capability adapters. Use app-owned tools
   only for opening/running native terminals. Foreground host skills route the
   descriptor, while the stdlib worker remains UI-independent. Ship explicit fallbacks
   if native open-and-run cannot be verified; no invented terminal API.
7. Run the full isolated scenario matrix and required package/docs/public checks.
   Review test quality and failure paths independently. Document precise supported
   host capabilities; perform bounded read-only native terminal smoke without model
   requests or user configuration writes. Actual account discovery stays separate.
8. In a follow-up after the reliability PR is ready for adoption, update #17 to the verified runtime, retain its
   tests/commits, correct the known fixtures through the new repair path, refresh red
   evidence and resume implementation. Validate the personal-account guard again.
   #17 must not freeze its invalid fixtures again or replay paid test authoring.

Use test helper contracts to expose fixture setup independently of product imports.
The known failures include trying a working-tree commit in a bare remote and creating
Git fixture repositories after hiding Git from PATH. Record these as distinct
portable regression cases, not copies of this task's unfinished test files.

Code ownership proposal: runner coordinates transitions; state owns journals and
leases; process owns children; verification owns setup/red/green evidence; providers
own normalization/identity; a small tracking module owns descriptors/capabilities;
CLI formats presentation. Keep new abstractions proportional to actual call sites.

## Delivery allocation

Manual implementation was committed on codex/workflow-reliability. The final
reviewable delivery is extracted onto codex/workflow-reliability-pr, in a separate
worktree based directly on main. It includes the needed report/account/recovery
repairs and project worktree guidance, excludes isolated-execution plan files, and
preserves both earlier task histories. The original pipeline manifest records the
manual source allocation; do not launch a duplicate task from the delivery checkout.
