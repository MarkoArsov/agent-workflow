---
title: Code map
description: Where plans, evidence, and runner code live, and what runs when you start a run.
question: Where do plans, evidence, and runner code live?
---

# Code map

!!! summary "In one minute"
    - Two places matter for a task: the **task checkout**, where code changes, and **`ai-plans/<task>/`**, where the agreed plan lives.
    - Run evidence goes to an ignored directory, by default `.agent-workflow/local/evidence/<task>/`.
    - The runner is ordinary standard-library Python under `runtime/agent_workflow/`, not an AI agent.
    - When something is unclear, `status`, the evidence files, and `inspect` answer most questions.

## The two places that matter for a task

| Place | What it contains | Why it is separate |
|---|---|---|
| Task checkout | The code being changed. Depending on the repository's profile, this is the current checkout, a feature branch, or a worktree under the configured worktree directory. | Keeps task work isolated from base checkouts and from other tasks. |
| `ai-plans/<task>/` | The confirmed plan: four Markdown files and `pipeline.json`. | Keeps the agreement about the work next to the code, in version control. |

Evidence is a third, ignored place. It records what the runner actually observed, so it never mixes with the plan you approved.

## Project map

~~~text
project/
├── PROJECT_WORKFLOW.md        # human-readable summary; setup manages one block
├── .agent-workflow/
│   ├── project.json           # the authoritative profile
│   ├── package-lock.json      # the pinned package version
│   ├── skills/                # your overrides and new skills
│   ├── rules/                 # scoped project conventions
│   ├── references/            # project guidance loaded on demand
│   ├── connectors/            # capabilities, never credentials
│   ├── stages.json            # optional custom stages
│   ├── local/                 # ignored: run lock, setup baseline, rule history
│   │   └── evidence/<task>/   # ignored: the run journal and evidence
│   └── runtime/               # ignored: a project-installed package
├── ai-plans/
│   └── csv-export/            # one task's plan
├── app/                       # a writable repository
└── checks/                    # a read-only companion repository
~~~

A single repository keeps the same layout at its root. The evidence path is the profile's `planning.evidence_directory`. See [project layout](projects.md) for how repositories join a project.

Inside a task's evidence directory:

| File | What it holds |
|---|---|
| `state.json` | The run journal: status, current stage, completed stages, attempts, checkouts, delivery progress, and any pending question. Written atomically. |
| `binding.json` | The plan, profile, skills, rules, and references this run is bound to. |
| `attempts/NNNN.json` | One agent or command attempt: route, session, classification, usage, cost when reported, and redacted output. |
| `evidence/STAGE-NNNN.json` | One verified stage: every check's command and parsed result, rule findings, changed paths, and the diff fingerprint. |
| `revisions/HASH.json` | The previous binding, archived by `resume --rebind`. |
| `runner.log` | Output of a detached runner. |

## What runs when you start a run

<!-- diagram: run-path -->

## Runtime modules

Everything below is standard-library Python with zero runtime dependencies.

| Module | Plain-language role |
|---|---|
| `cli.py` | The one command line used by skills and tests. Parses arguments and prints JSON. |
| `runner.py` | Binds the plan, runs preflight, executes stages in fresh sessions, verifies each one, retries within limits, and writes the journal. |
| `manifest.py` | Validates `pipeline.json`: stage order, repository access, writable paths, checks, outcomes, routes, delivery, and limits. |
| `verification.py` | Runs the named checks and parses unittest, pytest, .NET, Jest, TAP, or generic output into red or green evidence. |
| `git_ops.py` | Snapshots files, computes the diff fingerprint, guards writable paths, prepares checkouts, and performs guarded delivery. |
| `rules.py` | Evaluates the built-in secret detector and your blocking, advisory, and prose rules; records recurring examples. |
| `state.py` | Atomic run journals, the project lock, and cancellation requests. A stale PID never authorizes a kill. |
| `process.py` | Runs commands in their own process group with timeouts, inactivity and stalled-tool limits, and owned-only termination. |
| `providers/` | Builds the Claude Code, Codex, and Cursor commands for a route, and normalizes their events: session, final report, usage, and cost when reported. |
| `environments.py` | Disposable test services with leases, observed readiness, exported connection details, and owned cleanup. |
| `integrations/github.py` | `gh`-based reads of comments, issues, checks, and failure logs; draft pull requests; bounded bot polling. |
| `integrations/connectors.py` | Project connector declarations, headless availability checks, read-only command transports, and approved host configuration patches. |
| `setup.py` | Setup proposals with a three-way merge that keeps your edits, and apply-by-digest. |
| `detect.py` | Read-only detection of repositories, commands, and conventions, with the files each finding came from. |
| `extensions.py` | Resolves project skill overrides, creates new skills, and snapshots effective configuration for a run. |
| `profile.py`, `project.py` | Validate the project profile and resolve which project a directory belongs to, including worktrees and sibling repositories. |
| `install.py`, `adapters.py` | Versioned installation with receipts and rollback, owned-file uninstall, and host discovery entries. |
| `util.py` | Atomic writes, path containment, identifiers, hashing, and redaction. |

## What the runner does during a task

1. **Lock.** Takes the project's runner lock. A second runner is refused.
2. **Bind.** Loads the plan, checks every plan file is complete, and hashes the plan, profile, skills, rules, and references together.
3. **Preflight.** Validates the contract, repositories, effective skills, environments, connectors, and each provider CLI's flags.
4. **Run stages in order.** Each stage starts a fresh agent session, or runs your command for a custom command stage.
5. **Verify.** Checks changed files against the stage's writable paths, frozen tests, your pre-existing changes, and blocking rules, then runs the named checks itself.
6. **Record advisory findings.** Advisory rules and review notes go into the evidence and the run continues.
7. **Pause or fail only when it must.** A genuine question pauses the run. A scope or guard violation fails it at once; a failing check goes back to the agent as feedback and fails the run only when attempts run out.
8. **Journal everything.** State, attempts, and evidence are written atomically, so a run can be resumed or understood later.

## Where to look for an answer

| Question | Start here |
|---|---|
| What did we agree to build? | `ai-plans/<task>/requirements.md` and `pipeline.json` |
| Which files may change? | The `paths` and `test_paths` of each writable repository in `pipeline.json` |
| What is happening right now? | `agent-workflow status <task>` or `watch <task>` |
| Why did a check pass or fail? | `evidence/STAGE-NNNN.json` in the task's evidence directory |
| What did the agent actually say? | `attempts/NNNN.json` |
| What changed in a rebind? | `revisions/` and the `revisions` list in `state.json` |
| Which skill will a stage use? | `agent-workflow skill resolve <name>` |
| What is this project's configuration? | `agent-workflow inspect` |

## Important boundary

The runner records plans and evidence and guards outcomes after every stage. It is not, by itself, a complete security boundary around the machine it runs on.
Isolation, network egress, credentials, and branch protection need their own controls. See the [security boundary](security.md).

<!-- checkpoints: CTX-3, PST-2, EXE-5 -->

## See also

[Evidence and checks](verification.md) · [Open source](open-source.md) · [Project layout](projects.md)
