# Planning checks

Revision: full-contract-first specification, 29 October 2026.

- Preserved the previous complete proposal, facts and evaluator output under v2/;
  v1/ remains unchanged. Updated the current plan and model supplement coherently.
- Created all four canonical plan documents plus pipeline.json. Only planning
  artifacts changed; no implementation stage, product code or test was started.
- Read-only native model discovery initially failed in restricted execution.
  A retry outside that restriction succeeded: Codex advertised 8 models and
  Cursor advertised 269. This establishes listing evidence, not model entitlement
  or successful generation. No model inference or benchmark API request ran.
- Used an isolated temporary model store containing that discovery evidence for
  the existing models evaluate command implementation, with the resolved project's
  provider subset, legacy routes and any project model policy. It ran once for
  this revision. No global catalogue, defaults or project configuration were
  updated. The actual evaluator snapshot is saved as model-selection.json and
  embedded unchanged in pipeline.json, with only the three execution AI stages.
- `python3 bin/plovi validate-plan ai-plans/workflow-practices/pipeline.json`:
  passed, valid true. It checked the manifest and complete bound plan resources.
- `python3 bin/plovi preflight ai-plans/workflow-practices/pipeline.json`:
  passed. Stage skills, provider binaries/required flags, repository and references
  resolved. Permission mode is the project's trusted setting; no connectors or
  publication stages are selected. Account model access remains checked on the
  first actual provider request, as the existing preflight reports.
- Full implementation checks and specify scenario exercises are future work after
  approval. Neither native listing nor planning validation is a substitute for
  passing those checks. Preflight must run again against the approved contract
  at execution handoff if the files or environment changed.

Public-content scan: 689 items, zero findings; no external private denylist was
supplied. Whitespace/diff check and plan/snapshot consistency checks passed.
Unrelated concurrent setup/install/rename edits appeared during planning; they
were left untouched and are not part of the planning commit or allowed task scope.
Raw discovery/preflight outputs with local binary paths stay outside deliverables.
