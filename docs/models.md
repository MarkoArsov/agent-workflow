---
title: Cost and models
description: Where tokens are spent, why the machinery is cheap, and how routes keep you model-independent.
question: Why is it cheap, and why isn't it locked to one model?
---

# Cost and models

!!! summary "In one minute"
    - Most of plovi is Python and shell. Verification, status, watching, and delivery make no model calls.
    - The cheapest complete path is two sessions: `specify`, then `implement`.
    - Routes are chosen per stage: Claude Code, Codex, or Cursor, with the model you pick and explicit fallbacks.
    - Usage and cost are recorded only when the provider reports them. Unknown is never shown as zero.

## Why a complex workflow can still be cheap

A long chat that rediscovers the repository, re-reads huge logs, and retries until something looks green is expensive.
plovi writes the repeatable procedure down once as skills and scripts, then spends model tokens only on judgement.

| What looks expensive | Why it usually isn't |
|---|---|
| Many skills and reference files | A stage receives its one effective skill, the project's rules, and only the references the plan names. |
| An orchestrator, manifests, and evidence folders | Local scripts. They run commands, parse output, and write files. They bill no tokens. |
| Fresh sessions for tests, implementation, and review | Each is short and focused, and carries no long chat history into the next. Review is optional. |
| Verify and fix after implementation | Runs inside the `implement` session. The orchestrator's own verification is a script. |
| Watching a run | `status` and `watch` read the saved journal. No model. |
| Delivery | Commit, push, and draft pull request are scripts, with no provider route. |

The design rule is simple: if a decision is the same every time, write a script. If a judgement is needed, spend tokens on that judgement only.

## Where tokens are actually spent

| Session | When it runs | Typical job |
|---|---|---|
| `specify` | Always, before code | Research, questions, and a complete plan |
| `implement` | Always | Build the change and run the named checks |
| `implement-tests` | Full lane, when tests change | Write tests and prove they fail for the missing behavior |
| `review` | Only if selected | Independent look at the requirements and the diff |
| Custom skill stages | Only if you add them | Whatever the skill does |

A retry after a failed check is another session on the same route, with the observed failure as feedback. Attempts per route are bounded by the plan's limits.

## Not one model, provider, or harness

The plan is the contract: repositories, paths, checks, and evidence. The model is a worker behind that contract.

- Use one route for every stage, or a different one per stage.
- Give each stage an ordered list of fallbacks, or none. Authentication, quota, and unavailable-model failures move to the next route you approved.
- An answer to a paused question always resumes the session that asked. It is never rerouted.
- plovi ships reviewed seed assessments; native availability is discovered locally. Setup records the models you choose.

<!-- diagram: routes -->

**Scripts own the process. Models own the judgement. You choose the worker for each job.**

~~~json
{
  "pipeline": {
    "routes": {
      "default": [{"provider": "codex", "model": "YOUR_CODEX_MODEL", "reasoning": "high"}],
      "review": [
        {"provider": "claude", "model": "YOUR_CLAUDE_MODEL"},
        {"provider": "cursor", "model": "YOUR_CURSOR_MODEL"}
      ]
    }
  }
}
~~~

Routes set in the profile apply to every task; a plan may override them. Cursor effort belongs in its model expression rather than a reasoning flag.
See [commands and permissions](execution.md#routes).

## The cost knobs you actually have

1. **Lane.** Full contracts for substantive work; manual when explicitly requested or for a trivial low-risk edit.
2. **Review.** Skip it for a small change. Select it when the risk is higher.
3. **Route.** A cheaper or stronger model per stage, or one route for everything.
4. **Fallbacks.** Keep, reorder, or clear the ordered list before the run.
5. **Context.** Keep native instructions and project skills short; put lasting detail in references the plan names only when needed.
6. **Limits.** `attempts_per_route` (up to 5), `timeout_seconds`, `inactivity_seconds`, and `tool_timeout_seconds` bound every stage.
7. **Claude budget.** `execution.provider_settings.claude.max_budget_usd` passes a spending cap to Claude Code. Other providers' cost controls depend on their own interfaces.

If a run feels expensive, the usual causes are a plan that is too wide, a huge log reaching the model, or repeated rediscovery of a task that should have stayed bounded.

## Usage honesty

Each attempt records `usage` and `cost_usd` exactly as the provider emitted them.
A missing cost is `null`, meaning unknown, never zero. Provider doubles used in the test suite are labeled, and their usage is never described as real billing.

<!-- checkpoints: ORG-2 -->


## Refresh models and choose effort

Use **Update models** (`plovi-update-models`) to refresh native model catalogues,
confirm the providers and scope, and approve the proposed changes to machine or
project defaults. Other workflows keep separate settings. Refreshing the catalogue
does not change defaults, native app preferences or existing plans.

Every specify runs an offline evaluator using the task facts it already gathered.
It chooses suitable models and effort for the selected stages without an extra
model call. Routine work uses balanced effort; demanding stages may escalate.
Maximum effort requires an explicit choice. Missing effort metadata uses a valid
host default, and stale catalogues retain configured routes with a brief notice.

Explicit project routes remain pins. New adaptive defaults are resolved per stage,
and each approved task saves its chosen routes, effort, fallbacks and provenance.
Refreshes therefore do not change an approved or resumable task. Interactive hosts
must apply the recommendation themselves; writing a plan cannot switch the session.

The bundled registry records qualitative assessments and official sources. It is
not a benchmark ranking. Newly discovered models need reviewed assessments before
being recommended, and advertised availability is not proof of account access.

For CLI usage and settings examples, see the package's `references/model-routing.md`.
Run `models inspect`, `models refresh --providers <confirmed-hosts>`, and
`models evaluate`. The updater prepares `models propose --scope ... --input ...`
and applies only the user-approved digest with `models apply --approve ...`.
`models recover` restores an interrupted update without overwriting concurrent edits.

## See also

[Commands and permissions](execution.md) · [Code map](code-map.md) · [Lanes and bugfixes](lanes.md)


## Independent labs and optional benchmark evidence

The offline evaluator selects implementation first, test authoring next and review
last. It prefers suitable models from different labs, even through the same CLI;
a different CLI hosting the same lab is not independent. Limited availability is
honest: adversary-below-band explains a permitted one-band capability tradeoff,
single-lineage reports no alternate, and unknown-lineage keeps legacy custom entries
usable without claiming independence. Explicit pins and approved snapshots stay fixed.

`plovi models watch` fetches optional evidence with `AA_API_KEY`, or an explicitly
selected local assignment file via `--key-file`. It stores a dated machine-local
snapshot from the [Artificial Analysis API](https://artificialanalysis.ai/data-api/docs/reference).
Allowlisted fields include nullable indices, median performance, pricing and model
metadata. Reports cite [Artificial Analysis](https://artificialanalysis.ai/), distinguish
baseline from additions/removals, show index-version changes and identify gaps in
host discovery. API cost is not subscription cost; a benchmark does not prove access.

Missing keys or failed/partial fetches preserve prior evidence. No credential is
stored in the snapshot; do not put one in arguments, plans or tracked files. Exact
benchmark aliases start unverified/unmatched, so no model borrows another version
or effort variant's score. New/recent model reporting still works for known labs.

!!! note "What changes for your workflow"
    Update models can use benchmark evidence when you configure a key. It still
    shows the exact proposed settings diff for approval. Watching does not change
    routes, ranks or saved plans, and specify never needs a benchmark request.
