---
description: Choose provider models and interpret recorded usage and cost data.
---

# Models and costs

Choose routes for the work each stage performs.
You can use different providers or models for test authoring, implementation, and review.
The package does not bake a volatile model catalog into your project.

A route's fallbacks are ordered and explicit.
Authentication, quota, and unavailable-model errors move through that approved list.
Genuine input pauses stay with the original provider/session.

Fresh sessions reduce inherited assumptions between stages.
Stable instructions precede the changing task context, where the stage contract allows it.
Independent review excludes the implementation reasoning file.

Set bounded attempts and time limits.
Claude also supports a configured `max_budget_usd` setting.
Other cost controls depend on the provider's current interface.

Usage fields appear only when the provider emits them.
A missing cost is unknown, not zero. Simulated test usage is never described as real provider billing.

## Refresh models and choose effort

Use **AF Update Models** (`af-update-models`) to refresh native model catalogues,
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
