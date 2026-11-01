# Reliable autonomous implementation and tracking

The user requests a fresh review of the reference workflow and a plan to improve
plovi into a more dependable workflow/factory, including automatic tracking inside
the launching app when supported. Recommend delivery order relative to paused #17.
This is a planning invocation, not authorization to run agents or publish changes.

Full lane: implement-tests, implement, independent review. One writable repository:
agent-workflow. Task: workflow-reliability; branch codex/workflow-reliability.
Allocated through task start in the canonical project's configured task worktree.
Base: codex/isolated-execution at 5b2d2c3 (committed runner repairs only; unfinished
#17 test output is not copied). Canonical configuration root is the original
project registration, passed via --project; plans belong in this task worktree.
Private reference code was inspected read-only by explicit user request. Retain
only independently written behavioral requirements, never private source text,
identifiers, paths, credentials or account data in public deliverables.

## Implementation authorization

The user subsequently requested manual implementation with plovi-implement and a
PR after completion. This authorizes scoped implementation, verification, local
commits, normal push and a draft PR. Keep #17 stopped; its feature implementation
and evaluator changes remain a separate follow-up after reliability is ready.
