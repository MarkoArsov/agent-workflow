---
title: How it's tested
description: Automated coverage, real-host checks, and known limitations of plovi itself.
question: How do we know plovi itself works?
footer: reference
footer_order: 4
---

# How it's tested

!!! summary "In one minute"
    - The automated suite runs the real orchestrator against temporary repositories, local bare remotes, and labeled provider doubles, in an isolated home.
    - It covers setup, customization, red and green evidence, frozen tests, scope guards, retries, fallbacks, exact-session answers, recovery, installation, delivery, and environments.
    - CI runs it on Linux and macOS with Python 3.11 and 3.14.
    - A provider double is not a live model. Account-authenticated runs are checked separately with the real-host smoke procedure below.

The automated suite uses temporary repositories, bare local remotes, isolated homes/configuration, and labeled provider/connector doubles.
It never installs into a contributor's real agent settings or publishes to a real account.

| Area | Automated evidence |
|---|---|
| Setup | Preview/apply, stale approval rejection, re-run preservation, project membership. |
| Customization | Per-project overrides, new skills, custom stages, provider prompts. |
| Runtime | Red/green evidence, frozen tests, scope/index guards, fresh retries/fallbacks, exact-session input, stalls, interrupted recovery. |
| Installation | Global/project modes, rollback, updates, owned removal, compatible fallback, plugin relocation. |
| Git | Selected worktrees, parked/read-only repositories, base guards, partial delivery resume. |
| Integrations | Paginated feedback, connector availability/patches, bot draft restoration, rule recurrence. |
| Fixtures | Actual Python checks and an HTTP request to a disposable local application. |
| Environments | Readiness, exported connection details, shared leases, release requests, and cleanup on failed startup. |
| Target scenario | `tests/scenario` drives the whole target scenario against the provider double, a stateful GitHub fake and local bare remotes. [Each step's status](generated/scenario.md) shows how much works today. |

## Real-host smoke procedure

Vendor command-help and manifest validation are separate from model execution.
Local native Claude lifecycle and inventory checks have also been run in an isolated configuration.
A double passing does not prove account access, native discovery, or a provider's changing event format.

For each enabled host:

1. Use an isolated sample project and temporary host configuration.
2. Install the package or load the native plugin.
3. Confirm the setup skill is discoverable and resolves its effective file.
4. Create a project override; confirm direct invocation uses it.
5. Select a model available to that account and run a tiny implementation-only task.
6. Ask for a deliberate input pause; answer and verify the same session resumes.
7. Inspect actual evidence, usage fields, permission settings, and cleanup.

Account-authenticated generation, hosted GitHub publication, and GitHub Pages deployment are not claimed by isolated tests. Native Windows runs the same test suite and the PowerShell installer in CI.
See the local handoff for the specific checks performed for this release.

<!-- checkpoints: ORG-5, VER-2 -->

## Live smoke checklist

Doubles can't prove real providers, real GitHub, real CI, OS timers or a real staging host.
Each owning issue runs its item in its own pull request:

1. Use a disposable public sandbox repository with branch protection.
2. Run the check.
3. Record the result in `ai-plans/TASK/smoke-YYYY-MM-DD.md`: tool versions, the commands
   you ran, and what you observed.

| # | Check | Expected observation | Owner |
|---|---|---|---|
| L1 | Real providers: one task on Claude routes and one on Codex, `implement` + `review` to a PR | Sessions resume for fix rounds; token and cost fields are filled where the provider reports them | #47 |
| L2 | Real GitHub intake: label an issue yourself, and through an Actions workflow (a bot) | Only your label starts work | #21 |
| L3 | Real CI: a PR whose check fails on a planted defect | Readiness matches the GitHub UI; one fix round pushes to the same PR; CI turns green | #23 |
| L4 | Real auto-merge: required checks include `plovi/evidence`; `shadow = 0` in the sandbox | GitHub merges; `plovi pause --merges` disables auto-merge on another open PR; a revert suspends auto-merge | #23 |
| L5 | OS timer: `plovi schedule install-timer --apply` on macOS (launchd) and Linux (systemd) | A schedule fires on time with the captured `PATH`; `plovi doctor --as-timer` reports no differences | #20 |
| L6 | Real staging target: a sample app with a planted bug on a free host | One issue is filed; the next run comments instead of filing again | #50 |
| L7 | A real usage limit, or a deliberately low task budget | The task pauses with a reason (and the reset time when known) and resumes afterwards | #47 |
| L8 | Windows: one person-launched pipeline run with Codex or Claude | It completes to a PR; `.cmd` shims resolve | #46 |

## See also

[Contribute and develop](development.md) · [Checkpoint scorecard](scorecard.md) · [Open source](open-source.md)
