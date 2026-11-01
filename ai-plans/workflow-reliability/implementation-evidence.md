# Manual implementation evidence

The user selected manual implementation and draft-PR delivery. The implementation
is delivered on codex/workflow-reliability-pr, directly based on main, with the
needed predecessor repairs and without isolated-execution plans or unfinished tests.
The earlier source/history allocations remain intact. No native account settings,
release, merge or #17 run state was changed by this implementation.

## Verification

- Full isolated suite: `python3 -m unittest discover -s tests -v` — 316 tests, OK.
- `python3 -m mkdocs build --strict` — passed using the available documentation environment.
- `python3 scripts/check_links.py site` — 4331 internal links/assets, zero failures.
- `python3 scripts/generate_docs.py --check` — passed.
- `python3 scripts/generate_plugin_skills.py --check` — wrappers current.
- `python3 scripts/check_public_content.py --history` — zero findings; no custom private denylist supplied.
- `git diff --check` — passed.
- Disposable native POSIX terminal smoke: one detached fixture worker, automatic
  current-terminal watcher, running/complete human output, one provider request,
  no duplicate JSON summary. No real model generation or native login write.

## Acceptance mapping

| Outcome | Evidence |
|---|---|
| R1: stable runtime and entry point | Immutable source-copy/tamper/missing-runtime cases, active-upgrade refusal, repeated launch reuse, current run tracker identity in test_resume_recovery_v2 |
| R2: bounded classified correction | Two-round rejection/exhaustion, approved fallback once, explicit route preflight, malformed report and stalled-tool cases in test_autonomous_repairs and test_factory_journey |
| R3: independent fixture repair | Setup reproduction, fresh author/reviewer process identities, protected assertions, rejected-diff restoration, accepted proof and updated test hashes |
| R4: checked recovery | Retained output without another provider request, exact approved commit adoption, foreign file/index/commit refusal, commit/push/PR crash recovery, completed stages run once |
| R5: truthful tracking | Compact observer independent of large state, partial/rotated events, separate tool/activity/heartbeat state, stale-launch refusal and owned cleanup escalation |
| R6: host tracking | Capability/fallback/liveness/mode tests, native current-terminal smoke and Codex open-only panel smoke |
| R7: private identity | Wrong-account refusal before inference, selector-change refusal, unavailable required verification, existing account guard and isolated permission regressions |
| R8: portable factory journey | Disposable test authoring, fixture schema failure, independent correction/review, implementation, interruption, resume and final review once; full package/docs checks above |

## Before/after and review findings

The previous watcher could print the large baseline map. The compact-output
regression now proves that baseline/attempt contents stay out of ordinary watch.
Initial new feature checks exposed unsupported setup/report/tracker capabilities;
setup/import failures were not counted as behavioral red evidence.

A separate behavioral reproduction proved that a saved complete report could be
reused after its product file changed to foreign content. New artifact receipts
reject that exact case without another provider request and preserve the file.
Review also found cleanup failure during checks could enter another model attempt,
an active runtime receipt could be replaced, and an old launch could hide a resumed
stage. Targeted regressions now cover these paths. Existing question/approval exit
contracts remain unchanged; watchers signal action-required stops separately.

The final diff was reviewed against requirements and project quality guidance.
This manual review is not a claim that an external code reviewer approved the PR.
The fixture workflow's independent contexts are exercised with disposable providers.

## Limits and rollout

Codex panel opening/readback was observed, but no command-entry operation was
available. Native Claude VS Code and Cursor dedicated tracker execution remain
unverified. All hosts use supported foreground capabilities and an explicit command
fallback; no universal native open-and-run support is claimed. Known-cost limits
cannot bound unreported usage. Legacy output receipts without artifact hashes still
require full deterministic verification and do not gain provenance retroactively.

#17 remains stopped while this reliability PR is reviewed. Its feature/container
and evaluator work stays in its own allocation. Adopting this runtime and resuming
that task is a separate follow-up; do not rerun or edit its state just to complete
this delivery.
