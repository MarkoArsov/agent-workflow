# Model routing contract

`bin/plovi models` owns this workflow's settings. It never writes native
agent preferences. `models inspect` resolves paths and shows effective settings.
Machine state lives under the existing user data root's `models/`; project policy
lives in `.plovi/models.json`. Catalogues remain machine-local.

## Refresh and reviewed settings

`models refresh --providers codex,claude,cursor` lists models without generation.
Supply only the confirmed, allowed providers. Claude discovery returns configured
aliases/IDs needing explicit access confirmation with `--confirm-model claude:opus`.
Check managed policy and backend restrictions first. Discovery never establishes
entitlement and never promotes an unknown model on its own.

The seed registry is a dated qualitative starting point, not benchmark truth.
Official source URLs and review dates accompany its model/effort assessments.
New model IDs appear in `unreviewed_models`. Add relevant reviewed entries through
scope settings; no package edit is required. A registry entry has `provider`,
`model`, `family`, optional `lineage` (the model's lab slug), `band` (`fast`, `strong`, `deep`), `stages`, nonnegative `rank`
(lower is preferred), `confidence` (`reviewed` or `provisional`), `sources` and
`reviewed_at`. Optional `efforts` maps `simple`, `balanced`, `demanding` to supported
host values. Cursor instead uses exact IDs, `encoded_effort`, and a `modes` array.
Do not copy capabilities between aliases that resolve to different model versions.
API cost is not subscription cost; unknown usage remains unknown.

Settings use this structure (model names below are placeholders, not recommendations):

```json
{
  "global": {
    "schema_version": 1,
    "providers": ["codex"],
    "defaults": {
      "implement": [{"provider": "codex", "model": "chosen-id", "reasoning": "medium"}]
    },
    "pins": {},
    "blocked": [],
    "registry": []
  }
}
```

Use `project` instead of `global` for a project update, or both keys for `--scope both`.
Each scope object replaces that scope's settings: start with its existing values,
not an empty object. `defaults` and `pins` merge per stage across scopes; each route
array is atomic and contains primary then at most two recommended fallbacks.
`blocked` contains `provider:model` keys and combines across scopes. Provider sets
intersect with the profile and machine restrictions, including explicitly empty sets.
Existing project profile routes are pins. Explicit `adaptive_stages` in project
settings releases named legacy pins; explain this change in the proposal.

`models propose --scope global --input settings.json --output proposal.json`
creates a path-bound, digest-bound preview. Apply only after the user approves its
actual diff: `models apply --input proposal.json --approve <approval>`.
Backups, serialized writes, stale-file checks, atomic replacement, read-back and a
recovery journal protect settings. `models recover` restores an interrupted update;
it stops rather than overwriting external edits.

## Every specify

Write a small facts JSON using the task analysis already performed:

```json
{
  "stages": ["specify", "implement-tests", "implement", "review"],
  "kind": "code",
  "size": "medium",
  "risk": "standard",
  "uncertain": false,
  "repository_count": 1,
  "test_files": 2,
  "test_lines": 120
}
```

Use only selected AI stages, plus `specify` for an informational planning recommendation.
Size is `small|medium|large`; risk is `low|standard|high`. Missing facts retain balanced
choices. `demanding_stages` optionally narrows stage-specific capability escalation.
`complexity` accepts `simple`, `routine` (default) or `complex`. `stage_facts` maps
selected executable AI stages to overrides of kind, size, risk, uncertainty,
complexity and test counts. Absent keys inherit task facts; one stage's overrides
never affect another. Unknown stages/fields, invalid types/enums and negative or
nonfinite counts are rejected. Mechanical stages are ignored.

`routes` records attributable user/project overrides, not planner preferences.
`route_origins` can attribute each explicit stage as `user-task-route`, `project-pin`
or `global-pin`; absent legacy attribution is `legacy-explicit-route`. Metadata
records an origin, not proof of approval. Put planner ideas in `suggested_routes`,
validated route arrays that never pin, bypass availability, change capability,
provider or lineage constraints, or override pins. A suitable suggestion breaks
remaining ties after reviewed rank decisions.

Run `models evaluate --input facts.json --output model-selection.json` once. The
normal output is concise; `--verbose` shows provenance and bounded per-stage
`details`: effective facts/sources, band, effort mode/mapping, route source,
eligibility/exclusions, unresolved conditions, provider/lineage constraints and
ordered fallbacks. Route sources distinguish user-task-route, project-pin,
global-pin, legacy-explicit-route, retained-default and adaptive-selection. A pin
or retained default is never presented as a new adaptive recommendation. There are no network,
provider or extra model calls. No effort question or extra approval gate is added.
Small low-risk docs/config use the fast band; routine work uses strong; uncertainty,
high risk and large multi-repository work use deep for affected stages.
Capability and effort are independent: routine high-risk review can require deep
capability with balanced effort. Simple maps to simple effort, routine to balanced,
and complex/uncertain to demanding. Missing or unsupported reviewed effort mappings
omit the argument with an explanation; automatic routes never add xhigh/max/ultra. Four planned
test files or 300 expected test lines produce a size advisory; they do not by
themselves escalate capability or effort. Numeric facts must be
estimates from the plan, not invented certainty. Higher effort is not always better;
use reviewed model-specific mappings. Maximum levels are never selected automatically.

The evaluator selects implement first, then implement-tests, then review, without
changing pipeline execution order. Test authoring avoids implementation's lab;
review avoids both. A suitable alternate lab wins over a better rank from a used
lab; fallbacks prefer distinct labs too. The configured adversary policy permits
at most one band below the requirement when that is the only alternate, with
`adversary-below-band`. Otherwise `single-lineage` keeps a suitable in-band choice.
Legacy custom entries without lineage remain valid: an exact reviewed registry
match can supply lineage, otherwise it stays unknown with `unknown-lineage` when
independence cannot be established. Hosting the same lab through another CLI does
not make it independent. Advisories do not block execution or rewrite explicit
pins. Old 1.0 and 1.1 snapshots remain validated against their own recorded routes/hash.
Evaluator 1.2 changes selection semantics only for new evaluations; approved tasks
are never re-evaluated or rewritten during a package upgrade.

For a full plan, evaluate the executable AI stages and copy the saved result into
`pipeline.json.model_selection` and its `routes` into `pipeline.json.routes`.
For the full lane omit `specify` from the executable route snapshot; the active
planning model cannot be changed retrospectively. An unresolved
selection may be discussed while planning but cannot be executed. Explicit pins
below the recommended capability produce advisory feedback, not silent replacement.
For manual work, keep the compact route table; no detached pipeline is required.

A missing/stale catalogue keeps valid configured routes and adds one notice. Optional
missing effort metadata uses a valid host default; it does not block work. Saved
snapshots validate against their own recorded routes, not today's defaults. Changed
facts or routes require a new snapshot and normal plan revision. Runtime never re-runs
selection on approved plans. Aliases remain mutable; inspect actual execution reports.

## Stage-specific example

A large but routine test suite stays strong/balanced even beside uncertain work:

```json
{
  "stages": ["implement-tests", "implement", "review"],
  "kind": "code",
  "uncertain": true,
  "test_lines": 650,
  "stage_facts": {
    "implement-tests": {"complexity": "routine", "uncertain": false},
    "implement": {"complexity": "complex"},
    "review": {"risk": "high", "complexity": "routine", "uncertain": false}
  }
}
```

Implementation uses deep/demanding; tests use strong/balanced with a size advisory;
review requires deep capability but balanced effort. Exact models and argument
values still require reviewed suitability and host effort evidence. This is a
resource-use policy, not measured subscription or price optimization. Actual usage
and cost remain unknown without provider evidence.

To release profile route pins for later tasks, move their preference arrays into
project `defaults` and explicitly list the released stages (including `default` if
used) in project `adaptive_stages`. Keep the chosen provider subset. A missing
catalogue retains valid defaults with a warning; no configured route is unresolved,
and newly required capabilities still need evidence. Do not manufacture catalogue
access or add effort arguments without reviewed support.

## Independent distribution

The standard-library component is `runtime/plovi/model_policy` and imports
no runner code. `scripts/export_model_policy.py <target>/model_policy` exports a
standalone snapshot with checksums; `--check` detects drift. Locally edited exports
must be reviewed before replacement. Each export includes a portable contract check:
run `python -m model_policy.selftest` from its parent directory. Downstream adapters own their data paths and
provider restrictions. Updating this package never mutates another workflow's settings.


## Optional benchmark evidence

`models watch` makes one bounded request sequence to Artificial Analysis's free
language-model endpoint, using `AA_API_KEY` from the environment or an explicitly
selected `--key-file <path>`. Environment wins; a selected file is parsed for the
assignment, never executed. No other workflow's key file is searched. Never put a
key in arguments, settings, a proposal, a task plan, exports or version control.

The documented API contract is [Artificial Analysis's API reference](https://artificialanalysis.ai/data-api/docs/reference).
The allowlisted snapshot records source/date/tier/index version, model identity,
release/creator metadata, nullable headline/capability indices, median performance,
and input/output pricing. API price/speed is not subscription cost or task quality.
Attribute displayed figures to [Artificial Analysis](https://artificialanalysis.ai/).

The command replaces only machine-local `models/watch.json` after a complete valid
fetch. Missing key, HTTP/network errors, invalid/partial data or exhausted bounds
preserve prior evidence. Redirects are refused and error bodies are not printed.
A first snapshot is a baseline; later reports distinguish additions/removals and
same-version changes. Index-version changes suppress misleading score deltas.
Recent releases are bounded to dates within 45 days of today in UTC. Reports focus on the labs
of effective defaults/pins and distinguish missing/stale host discovery from a
missing exact ID or advertised access. Listing never establishes entitlement.

`model_policy/aliases.json` holds reviewed exact provider/model-to-benchmark mappings.
It starts empty because no exact version/effort mapping has been independently
verified for the seed entries. Unmapped routes stay unmatched; never guess or borrow
another effort variant's score. Review source/version evidence before adding a map.
This does not prevent reporting new/recent models for a known lab.

Watch is optional evidence for update-models, not input to offline evaluate. It
never changes ranks, suitability, defaults, fallbacks or approved plans. With no
key or a failed fetch, continue review using host discovery/official docs and label
any cached snapshot by date. Proposed settings still require exact-diff approval.
There is no recurring watcher or benchmark request on specify/run/resume.
