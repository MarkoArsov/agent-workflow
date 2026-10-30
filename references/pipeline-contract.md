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

Provider reports accept complete, needs_input, blocked, spec_conflict and impossible.
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
