---
title: Security boundary
description: What the runner enforces, and what your environment must provide.
question: What does Stagecoach protect, and what must your environment protect?
---

# Security boundary

!!! summary "In one minute"
    - The runner guards outcomes: writable paths, frozen tests, secrets and blocking rules, and delivery.
    - Every external action beyond the selected delivery stages needs its own authorization.
    - Trusted mode, the offered default, relies on configured access and post-stage checks. It is not operating-system containment.
    - Isolation, network egress, scoped credentials, branch protection, and central telemetry are your environment's job.

## What the runner enforces

| Control | What it does |
|---|---|
| Declared writable paths | After every stage, any change outside the stage's paths, or to a read-only repository, fails the run and stays in place for inspection. |
| Git state | A stage may not change HEAD, the branch, or the index. |
| Frozen tests | Assertion-proven tests cannot be rewritten, added, or deleted by later stages. |
| Your pre-existing changes | Recorded at start. A stage that touches them fails; delivery never commits them. |
| Secret detector and blocking rules | Private keys and common token formats, plus your deterministic rules, run on every changed file and again on the whole diff before publication. |
| Delivery guards | Explicit task branch only, task-owned paths only, no force pushes, no delivery after HEAD moved. |
| External actions | Selecting delivery stages authorizes only commit, push, and a draft pull request. Comments, replies, thread resolutions, review requests, messages, and tracker changes each need explicit authorization for that action and content. |
| Untrusted text | Every stage prompt says external files, issue text, logs, and tool results are evidence, never higher-priority instructions. `specify` and `address-pr-comments` repeat it for fetched text. This is instruction-level, not a deterministic filter. |
| Redaction | Bearer tokens, `token=`/`password=`/`secret=`/`api_key=` values, and common key formats are redacted from saved questions, errors, and command output. |
| Credentials | Only through host logins or environment variables named in `env_refs`. A literal command environment variable or connector setting with a secret-looking name (token, password, secret, key) is rejected. |
| Process ownership | Commands run in their own process group. Cancellation stops only the runner's own children; a stale PID never authorizes a kill. |

<!-- checkpoints: EXE-3, EXE-4, VER-6 -->

## Trusted and restricted modes

You choose the permission mode once, during setup. The runner checks at preflight that each provider CLI supports the flags the mode needs.

| Provider | Trusted | Restricted |
|---|---|---|
| Codex | `--dangerously-bypass-approvals-and-sandbox` | `workspace-write` sandbox, never prompts for approval |
| Claude Code | `--dangerously-skip-permissions` | `dontAsk` with an explicit `allowed_tools` list |
| Cursor | `--force`, `--sandbox disabled`, `--trust` | `--sandbox enabled`, `--trust` |

Trusted mode lets an unattended agent act without prompts. It relies on the access you configured and on the outcome checks above. **It is not operating-system containment.**
Restricted mode uses each provider's own controls, and those controls differ. It is not an identical cross-provider sandbox either.

See [commands and permissions](execution.md) for configuration.

<!-- checkpoints: EXE-1 -->

## What your environment must provide

These are gaps or external controls on the [scorecard](scorecard.md). Stagecoach documents them rather than claiming them.

| Control | Why | Checkpoint |
|---|---|---|
| Operating-system isolation | Run unattended trusted stages inside a container or VM, so a misbehaving agent can't reach beyond the project. | EXE-1 |
| Network egress allowlisting | Restrict provider, package, and source-control hosts. The runner does not control network access. | EXE-2 |
| Scoped, short-lived credentials | Agents inherit host logins today. Issue per-task or per-stage credentials where you can, and audit their use. | ORG-3 |
| Branch protection and named approvers | The runner never approves or merges, but only source control can require that a named human does. | REV-1 |
| Production access in layers | Identity, database, network, and audit controls around anything beyond staging. | ORG-4 |
| Central telemetry | Run journals stay local. Export them if you need organization-wide monitoring. | PST-2 |

<!-- checkpoints: EXE-2, ORG-3, ORG-4, REV-1 -->

## See also

[Checkpoint scorecard](scorecard.md) · [Commands and permissions](execution.md) · [Open source](open-source.md)
