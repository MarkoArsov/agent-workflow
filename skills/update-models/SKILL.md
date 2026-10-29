---
name: update-models
description: Refresh available models and recommend task routes and effort; review changes to this workflow's machine or project defaults.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/plovi for commands. Without a configured project, use this package's global command.
<!-- resolver:end -->

# Update models

Read the selected package's references/model-routing.md for the settings and task-facts format.

1. Run `models inspect`. Confirm this workflow's machine defaults, the resolved project, or both as the target. Show the actual target paths. Confirm the allowed provider subset; an installed CLI is not proof of account access. Do not update another workflow or native application preferences.
2. Run `models refresh --providers <confirmed,hosts>`. This only refreshes discovery evidence. For Claude, check the backend, applicable managed/local restrictions and actual account access with the user; pass `--confirm-model claude:<advertised-id>` only for confirmed access. Do not claim the catalogue proves entitlement. Preserve existing defaults when discovery fails.
3. When AA_API_KEY is configured, run models watch (or use --key-file for an
   explicitly selected local assignment file). It fetches optional Artificial
   Analysis evidence, not new defaults. Attribute displayed figures to
   https://artificialanalysis.ai/ and include date/index version. Missing key or
   failed fetch leaves previous evidence unchanged; explain that limitation and
   continue with discovery/official docs, labeling any cached evidence by date.
   Never inspect another workflow's credential file or create a recurring job.
4. Review only relevant new or changed candidates against official model/effort documentation. Native IDs and supported efforts come from discovery. Store proposed assessments with source URLs, date, family, suitability band, stable preference rank and model-specific effort mappings. Newer is not automatically better. Unreviewed candidates stay unselected. Benchmark presence is not host access or task suitability. Unmatched exact model/
   effort aliases stay unknown. Watch never rewrites rank, suitability or routes;
   use evidence to review assessments before proposing settings.
5. Run `models evaluate` for routine defaults; use task-facts input to compare demanding work if useful. Honour project pins. Explain adversary-below-band, single-lineage and unknown-lineage advisories; a CLI is not a model lab. Draft complete settings objects for the selected scopes, preserving existing fields and incorporating reviewed registry additions. Compare those additions with `models evaluate --settings <settings.json>` without applying them. Use the smallest supported effort suitable for the work. Maximum effort requires an explicit choice.
6. Run `models propose --scope <global|project|both> --input <settings.json> --output <proposal.json>`. Present old → new routes, effort, ordered fallbacks, reasons, confidence, and which project pins mask global changes. Ask approval of this exact scope and diff. Do not infer settings approval from permission to refresh.
7. After approval, run `models apply --input <proposal.json> --approve <digest>`. Report the reread effective values. If files changed, regenerate and show the proposal. An interrupted apply has `models recover` to restore its journaled previous values, preserving concurrent edits.

Every specify uses the offline evaluator; do not create a recurring refresh job unless requested. Do not change approved task snapshots, stages, permissions, checks or retry limits. Interactive sessions must apply model changes through their host; a recommendation cannot switch the current session by itself.
