# Full plan contract

Use this reference when authoring a pipeline.json. Replace example repository IDs,
paths, model names, checks, and outcomes with confirmed project facts. Keep all four
plan files complete alongside the manifest.

Substantive work defaults to this full contract. Manual is an explicit user choice
or a clearly trivial low-risk edit, with its reason recorded. A missing route keeps
the full contract a draft; it is not a reason to silently select manual execution.
Run validate-plan and preflight before reporting a contract ready, distinguishing
their actual results from planned checks. Specification still ends at approval.

Allocate the configured task checkout with task start before writing a new plan; task/repository
and branch/base selection does not require an existing manifest. Keep single-repo
plans inside that checkout, or use the configured multi-repository plan owner/shared
store. Record the chosen branch for execution handoff and reuse that worktree.
Unmarked legacy current-checkout does not bypass new-task isolation. Only resume the same
task with its receipt; never move dirty/staged work automatically.

Planning commits and checkout allocation are separate decisions. New tasks default to
the owned task worktree above and honor explicit setup overrides; legacy approved manifests retain their checkout
strategy. When native instructions or project policy require planning commits,
commit the complete contract and task-owned supporting artifacts in the plan-owning
branch before handoff. Do not include unrelated changes or push. An unversioned
shared plan store remains unversioned unless the user selects a configuration
repository.

The handoff links requirements.md and pipeline.json, names each actual branch as
created or reused with its checkout strategy, and gives the planning commit hash
or an explicit uncommitted limitation. An optional plan.md is a summary, not a
replacement for the contract below.

Include `quality-guidance.md` and applicable project quality names in `references`; see
`quality-guidance.md`. All three AI stages receive those frozen sources, with
project references taking precedence. Do not put implementation reasoning into a
reference shared with independent review.

~~~json
{
  "schema_version": 1,
  "task": "greeting",
  "plan_files": ["prompt.md", "requirements.md", "implementation.md", "deferred.md"],
  "repositories": [
    {
      "id": "app",
      "access": "write",
      "branch": "feature/greeting",
      "paths": ["src/**", "tests/**"],
      "test_paths": ["tests/**"]
    },
    {"id": "checks", "access": "read"}
  ],
  "stages": ["implement-tests", "implement", "review"],
  "checks": [
    {
      "id": "greeting-behavior",
      "repository": "app",
      "command": {
        "argv": ["python3", "-m", "unittest", "-v", "tests.test_greeting"],
        "cwd": ".",
        "timeout_seconds": 300
      },
      "parser": "unittest",
      "identities": ["test_greeting"],
      "phases": ["red", "green"]
    }
  ],
  "outcomes": [{"id": "greets-the-requested-name", "checks": ["greeting-behavior"]}],
  "limits": {
    "attempts_per_route": 2,
    "timeout_seconds": 1800,
    "inactivity_seconds": 300,
    "tool_timeout_seconds": 600
  },
  "references": [],
  "connectors": []
}
~~~

Routes inherit from the project or are explicitly selected in the plan. A stage
maps to an ordered array of provider/model objects; default is the fallback key
for an unspecified stage. A reasoning setting is optional.

Checks can name a repository command by string instead of repeating its object.
Generic checks need success_pattern and, for red evidence, failure_pattern.
Expected red test identities must appear as failed assertions. When implement-tests
cannot fail on assertions before product changes, declare no red checks and set
approved_no_red_reason to where red is demonstrated instead; its checks then run green. Commands that modify
source invalidate their own evidence.

Selecting commit-and-push requires delivery.commit_message and an explicit non-base
branch on every writable repository. Selecting draft-pr additionally requires
delivery.title and delivery.body_file, relative to the plan directory. This selects
only those actions, not reviewer requests or tracker updates.

Custom stage definitions come from the project's stages.json and are included by
ID in the ordered stage array. Check IDs refer to this plan's checks. Inputs are
exact repository-relative files; outputs may use declared path patterns.

## Runner outcomes and policy

Provider reports accept complete, needs_input, blocked, spec_conflict, impossible and test_fixture_repair.
needs_input requires a nonempty question; escalations require a nonempty reason.
Optional assumptions are strings in an array. Malformed reports are not evidence.
Escalations stop attempts/fallbacks immediately; retry retains history and starts
fresh. Ordinary resume cannot clear an escalation or pending diff approval.

plovi.toml supplies reviewed per-key policy beneath explicit plan limits and above
profile/built-in defaults. Limits default to 40 files, 1500 added/removed lines,
two attempts per route. Protected paths and size gates require separate approvals
bound to path/content/mode fingerprints. Unattended runs default to restricted.
Policy and permission provenance are saved with the binding; changes require rebind.
Legacy bindings without policy retain their legacy inputs until explicit rebind.

New setup profiles default to worktree and planning.commit_plans=true. Setup can
review explicit checkout choices and local-only plan commits. Unversioned
shared plan stores require an explicit plan-owning repository or reviewed opt-out.
The complete contract, evaluator, quality and evidence artifacts are committed
locally on the task branch before approval handoff. Verify each artifact in the
commit; never claim a summary-only commit delivered the contract.

Each task holds its own runner.lock; short repo-ops critical sections protect Git
mutations and claims. Only disjoint worktree tasks share a repository. Claims are
released at pauses and completion; stale ownership uses OS locks, never PIDs.
Recovery persists delivery intent, adopts exact commits, reconciles remote branches,
and synchronizes one managed PR Evidence section from verified runner state.

The task-start result records branch, checkout, plan path and canonical configuration
root without needing a manifest first. Include the allocated branch for each writable
repository; runner preparation uses the owned receipt and rejects changed ownership.
Read-only companions remain untouched. Old manifests retain legacy execution semantics.

## Fixture setup and bounded correction

Checks may declare setup with green semantics. Fixture-health commands must exercise
helpers before product APIs exist; imports/startup are not assertion-red evidence.
Test authoring must pass setup before tests freeze. A later test_fixture_repair
report requires reason, test_paths=[{repository,path}] and checks=[setup-check-id].
It authorizes only a fresh approved test-author route and independent review within
declared test paths; it never permits implementation to edit frozen tests directly.
The runner guards test identities/assertions/deletions/skips, saves originals and
diffs, and accepts new fingerprints only after review, setup and applicable proof.
Mechanical rejection can reauthor within the bounded budget; weakening or changed
requirements stop. Failed requests without file edits may use approved fallback
routes once each; identity mismatch stops before requests.

Optional corrections.fixture_rounds is 0–5 (default 2), per implementation/review
stage. Optional corrections.max_known_cost_usd bounds reported usage before another
request. Missing usage stays unknown, so this is not a guaranteed total-spend cap.

The pipeline entry point starts or recovers a task with an immutable runtime receipt.
Runtime changes require --upgrade-runtime --rebind; originals and recovery journals
remain available. Trackers use structured argv/cwd from that runtime. Host UI runs
only in the foreground adapter, with truthful capability/liveness acknowledgements.
Status/watch defaults to human output; --json emits versioned summary/event objects.

## Explicit legacy checkpoint handoff

`recovery.test_checkpoint` requires original binding_sha256 and escalation_sha256
values, with an optional test_fixture_repair fixture_request. This is explicit
migration authorization, not evidence that a requirements decision is mechanical.
Migrate validates unchanged requirements/checks/outcomes/routes/ownership, frozen
hashes and passing old stage evidence, then renews fixture setup and red proof.
It preserves the completed test stage and stops at implementation. Original state
and binding are archived. Repeated identical handoff does not repeat inference.

An exact merge in approved_commits must also appear in approved_merges and is
admissible only during reviewed rebind/migration. All ancestors introduced by the
merge still need exact approval or the existing task-plan-only exception. Baselines
adopt the first-parent tree differences; unrelated edits and frozen-test changes
remain guarded. Linear recovery behavior remains unchanged by default.

## Bounded contract reconciliation

Optional corrections.contract_review_rounds (0–2; legacy default 0) lets a fresh
review route classify spec_conflict reports before escalation. Only independently
confirmed test-input/setup mistakes within unchanged approved requirements proceed.
A fresh test author receives declared test paths; assertions, cases and skips remain
protected. A second independent review and setup/red proof precede renewed hashes.
When product work already exists, failed green checks feed implementation correction;
final verification is still mandatory. Requirements/account/authorization decisions,
assertion changes, foreign edits and exhausted budgets remain stops. Save original
files, classifications, diffs and review/check evidence in contract-reviews.

## Factory and execution boundary

New unattended tasks select factory checkouts; interactive strategies remain
configurable. Effective strategies are bound into claims and state. Resume keeps
its recorded allocation, including legacy local semantics. Factory snapshots guard
the task-owned writable and detached companion trees, independent of user clones.
Container mode requires those factory receipts and a preflight-pinned image ID.
It covers AI attempts, independent repair/review attempts, custom commands, named
checks, verify and environment services. Runtime guards and selected delivery stay
host-side. Policy/bindings contain API variable names, never their values. See
[isolated execution](../docs/isolation.md) for mounts, failure and cleanup semantics.
