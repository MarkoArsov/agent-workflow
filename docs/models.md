---
title: Cost and models
description: Where tokens are spent, why the machinery is cheap, and how routes keep you model-independent.
question: Why is it cheap, and why isn't it locked to one model?
---

# Cost and models

!!! summary "In one minute"
    - Most of Stageway is Python and shell. Verification, status, watching, and delivery make no model calls.
    - The cheapest complete path is two sessions: `specify`, then `implement`.
    - Routes are chosen per stage: Claude Code, Codex, or Cursor, with the model you pick and explicit fallbacks.
    - Usage and cost are recorded only when the provider reports them. Unknown is never shown as zero.

## Why a complex workflow can still be cheap

A long chat that rediscovers the repository, re-reads huge logs, and retries until something looks green is expensive.
Stageway writes the repeatable procedure down once as skills and scripts, then spends model tokens only on judgement.

| What looks expensive | Why it usually isn't |
|---|---|
| Many skills and reference files | A stage receives its one effective skill, the project's rules, and only the references the plan names. |
| A runner, manifests, and evidence folders | Local scripts. They run commands, parse output, and write files. They bill no tokens. |
| Fresh sessions for tests, implementation, and review | Each is short and focused, and carries no long chat history into the next. Review is optional. |
| Verify and fix after implementation | Runs inside the `implement` session. The runner's own verification is a script. |
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
- Stageway ships no model catalog. Setup records the models you choose.

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

1. **Lane.** The manual lane for an isolated change; the full lane when independent tests, review, or delivery are worth it.
2. **Review.** Skip it for a small change. Select it when the risk is higher.
3. **Route.** A cheaper or stronger model per stage, or one route for everything.
4. **Fallbacks.** Keep, reorder, or clear the ordered list before the run.
5. **Context.** Keep native instructions and project skills short; put lasting detail in references the plan names only when needed.
6. **Limits.** `attempts_per_route` (up to 5), `timeout_seconds`, `inactivity_seconds`, and `tool_timeout_seconds` bound every stage.
7. **Claude budget.** `execution.provider_settings.claude.max_budget_usd` passes a spending cap to Claude Code. Other providers' cost controls depend on their own interfaces.

If a run feels expensive, the usual causes are a plan that is too wide, a huge log reaching the model, or the full lane on a one-file follow-up.

## Usage honesty

Each attempt records `usage` and `cost_usd` exactly as the provider emitted them.
A missing cost is `null`, meaning unknown, never zero. Provider doubles used in the test suite are labeled, and their usage is never described as real billing.

<!-- checkpoints: ORG-2 -->

## See also

[Commands and permissions](execution.md) · [Code map](code-map.md) · [Lanes and bugfixes](lanes.md)
