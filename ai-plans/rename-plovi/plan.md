# Rename to plovi

Status: proposed; implementation is not approved.
Source and unchanged acceptance criteria: [prompt.md](prompt.md).

## Execution and delivery

Use the in-session lane, in this checkout, with tests first, implementation, then
a final requirements/diff review. This is a broad but coordinated rename in one
repository, including the workflow's own bootstrap and discovery paths. Keeping
the operation in the active session avoids a detached runner depending on entry
points that this task replaces. No pipeline manifest or detached stages are
selected. No subagents or independent-review claim are included.

One writable repository: the profile's `agent-workflow`, path `.`. The working
tree was clean at research start, on the completed CI task branch. Create a local
`codex/rename-plovi` branch for this task; preserve the CI commits. Do not push or
change the base branch. Before implementation, verify the approved starting
revision and preserve any intervening user edits. Use Python 3.11+ and the
standard library for runtime, installation, migration, and tests.

Execution permission mode: the existing project setting, `trusted`, within this
scope. Tests always use allowlisted child environments, temporary repositories,
temporary homes, and isolated host configuration. No real user installation,
configuration, catalogue, plugin cache, or project registry is modified.

Local delivery: commit the plan separately as `Plan the plovi rename`; after
approval and successful checks, commit logical implementation changes, ending
with `Rename the workflow to plovi with compatible aliases`. No push, PR,
publication, release, deployment, tracker update, or message to another person
is selected. Those require a separate explicit request.

## Evidence and existing conventions

- `workflow-package.json` centralizes the public discovery prefix. Canonical
  skill IDs and project override keys are independent of public names in
  `runtime/agentflow/adapters.py` and `runtime/agentflow/extensions.py`.
- `runtime/agentflow/project.py` resolves explicit membership, project references,
  nested paths, registered worktrees, and the user registry. Migration must not
  accidentally absorb an unrelated ancestor project.
- `templates/adapters/launch.py`, `templates/adapters/dispatch.py`, and bundled
  `skills/*/scripts/resolve.py` bootstrap before runtime project resolution.
  Changing only the runtime resolver would leave installed entry points broken.
- `runtime/agentflow/install.py` owns versioned payloads, receipt hashes,
  rollback, linked installations, discovery collisions, and ownership-aware
  uninstall. Preserve those contracts for both new names and aliases.
- `runtime/agentflow/util.py:user_data` already supports an older global data
  location for linked installs. Global receipts, model settings, and pinned
  packages need a compatibility path through this rename too.
- `runtime/agentflow/setup.py` owns managed instruction blocks, setup baselines,
  and reviewed changes. Recognize legacy markers before producing new markers;
  do not append a second managed block or discard custom prose.
- Existing regression examples: `tests/test_install.py`, `test_resolution.py`,
  `test_setup.py`, `test_release.py`, `test_ci_workflow.py`, and `tests/helpers.py`.
  CI's Windows harness currently invokes the old command and discovery name.
- `scripts/generate_docs.py`, `scripts/docs_content.py`, `docs-data/`, and site
  templates refer to runtime paths and command names. Generated pages must be
  regenerated from their sources. `templates/site/main.html` also has an obsolete
  rename banner; its copy should become a current plovi rename notice.
- `design/README.md`, `design/DESIGN.md`, and `design/tokens.json` govern visible
  output. Existing design references already use plovi. No restyling, token,
  typography, layout, icon, or logo-geometry changes belong to this issue.
- Native Claude plugins namespace skills under their plugin name; custom skill
  directories supplement the default `skills/` directory. See the official
  [manifest reference](https://code.claude.com/docs/en/plugins-reference).
  Do not confuse standalone `/plovi-review` with plugin-qualified invocation.

## Writable scope

- Rename `runtime/agentflow/**` to `runtime/plovi/**`; add the narrow migration
  module there. Rename internal imports and module invocation strings throughout
  runtime and package tooling. No legacy Python import package is promised.
- `bin/plovi`, the compatibility `bin/agentflow`, `workflow-package.json`,
  `pyproject.toml`, `install.py`, `install.sh`, `install.ps1`, `.claude-plugin/**`,
  `templates/adapters/**`, `templates/plugin-skills/**` if needed for generated
  native discovery, `skills/**`, `references/**`, and `schemas/**` as needed for
  names, discovery, and migration only.
- `scripts/**` for renamed imports, generated discovery, release/checksum paths,
  host smoke checks, and a focused old-name audit. `.github/workflows/**` only
  for command/path/skill-name references; preserve CI triggers and job behavior.
- `tests/**`: rename existing imports/fixtures and add focused regressions.
- `.agentflow/**` to `.plovi/**` for this repository's tracked project profile
  and package lock only. Do not move ignored real local runtime state as part of
  implementation. Update `.gitignore`, `PROJECT_WORKFLOW.md`, `AGENTS.md`,
  `CLAUDE.md`, and `.claude/CLAUDE.md` only for applicable names/managed markers.
- README, HANDOFF, PLAN, current references in tracked planning documents,
  release/history notes, `docs/**`, `docs-data/**`, `mkdocs.yml`, and
  `templates/site/**`: words, paths, accessible labels, generated references,
  and text-bearing brand assets only. Preserve factual historical evidence;
  retain necessary quotations of former names as explicit changelog entries.
  Any raster derivative containing the old written name must be regenerated
  from the text-updated source, preserving its existing visual treatment.

## Requirements and implementation sequence

1. **Behavioral red evidence first.** Add tests that can execute against the old
   checkout without importing a nonexistent `plovi` package. Use subprocess
   installation and the existing runtime behind a test helper where necessary.
   Assert the new executable, names, migration result, and alias warnings so red
   failures are assertions about behavior, never missing imports, syntax errors,
   or shell startup failures. Then update remaining tests to the new imports.

2. **Canonical names and entry points.** Make `plovi` the package marker,
   Python module, executable, installer output, default discovery prefix,
   plugin/marketplace name, and release archive prefix. Use lowercase in titles,
   UI labels, help, errors, schema descriptions, metadata, and docs. Preserve the
   version and schema version unless a concrete compatibility requirement proves
   otherwise. Keep canonical skill IDs, stage IDs, user-selected model routes,
   permission settings, and behavior unchanged.

3. **Launcher compatibility until 1.0.** Install both commands, including Windows
   `.cmd` shims. `agentflow` delegates arguments and exit status to the same
   implementation as `plovi`, emitting exactly one line on stderr per invocation:
   `agentflow is now plovi; use plovi (alias available until 1.0).`
   Normal stdout, JSON output, `--help`, `--version`, cancellation, and signals
   retain their meaning. Do not warn on canonical commands.

4. **Skill compatibility until 1.0.** Generate both `plovi-<name>` and
   `af-<name>` discovery entries for every bundled skill and project extension
   supported by the existing discovery mechanism. Both map to the same canonical
   ID, effective project override, and pinned runtime. The alias dispatcher emits
   one stderr line naming the replacement; its stdout remains only the effective
   skill path. Respect existing explicit presentation aliases. Check collisions
   across both name sets before writing, retain edited/unowned adapters, and keep
   receipt-owned refresh, rollback, and uninstall correct for both sets.

   Claude standalone discovery follows the same names as Codex and Cursor.
   Native plugin discovery also exposes the prefixed entries through generated
   thin wrappers that use the common dispatcher, rather than duplicating skill
   bodies. Use an additional payload-contained directory, such as
   `templates/plugin-skills/`, declared in the manifest and generated/checkable
   with the package tooling. Plugin-qualified examples are
   `/plovi:plovi-implement` and its `/plovi:af-implement` alias; retain canonical
   bare skill IDs for internal lookup. Validate the native names against the
   installed host in an isolated home and document the namespace accurately.

5. **Project migration on first applicable run.** Make `.plovi/` the canonical
   project configuration directory. Discover both names before choosing the
   runtime so a legacy project-only install can reach the migration code.
   Only migrate a project or registered child reference that belongs to the
   selected project; an unrelated ancestor stays untouched. Cover direct source
   CLI, installed launchers, both skill names, explicit `--project`, nested paths,
   multi-repository children, and registered Git worktrees.

   When only the legacy directory exists, serialize migration outside the folder
   being moved, validate its type and ownership context, and move the whole tree
   without overwriting a destination. Preserve arbitrary files, permissions,
   extensions, credentials, logs, baselines, receipts, and package pins. Rebase
   only known path-bearing configuration fields and installer-owned references
   that point inside the moved directory: profile extension/evidence/worktree
   paths, receipt keys and owned hashes, active payload pointers, generated
   launcher paths, and setup baseline keys. Custom locations outside that tree
   remain unchanged. Do not globally replace strings inside user files or saved
   plan/model snapshots.

   Make path rebasing recoverable with a small transaction record and backups of
   changed metadata; test interruption before/after the move and during rebasing.
   Concurrent invocations must converge on one successful migration. Print one
   stderr notice after successful migration, then remain quiet on subsequent runs.
   Canonical-only projects are unchanged. If both folders exist, or a directory
   is a symlink/unsupported entry, stop with a recovery instruction and change
   neither tree. Do not merge or delete either folder automatically. Detect an
   active runner and require it to finish or be cancelled before migration;
   preserve completed/cancelled evidence and reject stale resume bindings as the
   current runner already does. Live-task migration is not included.

   Honor preview-only setup/install/dry-run contracts: report a pending migration
   without making it during a preview. Perform it on the first applicable normal
   execution or explicit installation/setup apply. Bare help/version should not
   mutate an unrelated project's files.

6. **Existing installations and setup.** Fresh global data uses the plovi name;
   existing receipt-owned global data remains readable through a documented legacy
   fallback, including the existing pre-rename linked-install case. Do not move
   or discard machine-wide state merely to rename it. Reinstallation must reuse
   ownership rather than treating old wrappers as foreign, keep pinned older
   payloads usable, and preserve model policy/settings. Bootstrap selection must
   inspect the selected payload's marker and import its matching runtime module;
   an older pinned payload still has the legacy module name. Test both an older
   project pin under a new global install and a migrated project-only pin, rather
   than assuming every selectable payload already contains the renamed module.
   Prefer the new package override environment name while accepting the old variable as compatibility
   input. Recognize old managed markers, replace the managed region once, preserve
   custom surrounding prose, and maintain no-op re-setup behavior. Rename native
   plugin metadata and lifecycle commands; explain native reinstallation rather
   than editing host plugin caches. Test relocation and checksum validation.

7. **Documentation and complete name audit.** Update current command examples,
   skill names, profile paths, code maps, diagrams, generated references, help,
   accessible labels, and text in existing logos/social cards. Leave the GitHub
   repository name, public repository URLs, domain, visual design, and design
   source assets unchanged. Include a brief "What changes for your workflow"
   callout: reinstall, prefer the new names, finish/cancel running tasks first,
   automatic project migration, aliases available until 1.0.

   Add a focused audit over tracked deliverable text and built documentation for
   case-insensitive old product names. Classify every remaining match: aliases,
   migration/legacy compatibility code, explicit changelog entries, or tests of
   those behaviors. Use narrow file/line or contextual exceptions, not an
   unrestricted runtime/docs allowlist. Include hidden tracked configuration;
   exclude Git internals, dependencies, local evidence, and historical commit
   contents from the rename audit. The separate public-content history scan
   still runs. Also inspect text-bearing raster assets visually because text
   search cannot detect their pixels.

## Executable checks and acceptance mapping

All commands run from repository root. New test method names below are planned
identities, not claims that the tests already exist. Use unittest parsing;
targeted checks have 180-second limits, the full suite 600 seconds, docs and
release 180 seconds, public-history audit 300 seconds. A failing assertion in the
named method is the red proof; an import/build failure is never red evidence.

| Outcome | Executable check and required observation |
| --- | --- |
| New CLI and compatible launcher | `python3 -m unittest discover -s tests -p test_rename.py -v`; planned `test_fresh_install_has_plovi_and_legacy_launcher`, `test_alias_preserves_output_arguments_and_exit_status`: fresh install exposes both, canonical help is plovi, alias has one stderr notice and identical exit/output semantics. These produce assertion red before implementation. |
| Lossless first-run migration | `python3 -m unittest discover -s tests -p test_migration.py -v`; planned `test_legacy_project_moves_without_data_loss`, `test_repeat_run_does_not_repeat_notice`, `test_rebased_profile_and_receipt_remain_usable`: compare arbitrary file bytes/modes and actual extension resolution; first two produce assertion red on the old checkout. |
| Safe migration and discovery | Same migration suite: planned `test_both_directories_preserved_on_conflict`, `test_interruption_recovers_without_loss`, `test_concurrent_first_runs_migrate_once`, `test_unrelated_project_is_not_migrated`, `test_preview_does_not_migrate`, `test_active_runner_blocks_migration`. Include nested/explicit roots, child references, worktrees, installed project runtime, custom paths, and symlinks. |
| Both skill names work on all supported hosts | Rename suite: planned `test_all_host_skill_aliases_resolve_same_override`, `test_native_plugin_prefixed_entries_and_aliases`, `test_discovery_alias_collisions_preserve_user_files`. Assert generated names, descriptions, resolved paths, canonical IDs, clean stdout, and alias-only stderr warnings. Prefixed-entry assertions can fail behaviorally before implementation. |
| Existing install lifecycle preserved | `python3 -m unittest discover -s tests -p test_install.py -v`, plus `test_resolution.py`, `test_setup.py`, and `test_model_policy.py` via the same discover pattern. Cover global/project/linked installs, old receipts, older project pins, model settings, failed installs, edited adapters, no-op setup, and owned uninstall. |
| Release, plugin, CI integration | `python3 -m unittest discover -s tests -p test_release.py -v` and the same command for `test_ci_workflow.py`; deterministic payload/checksums include the canonical launcher, alias, native wrappers, and PowerShell installer. CI invokes the new command with isolated Windows homes. |
| Whole-package behavior | `python3 -m unittest discover -s tests -v`; all isolated tests pass. Linux/macOS/Windows native results are separate evidence, not inferred from local doubles. |
| Documentation and generated references | `python3 scripts/generate_docs.py --check`; `python3 -m mkdocs build --strict`; `python3 scripts/check_links.py site`; source references, runtime paths, navigation, anchors, and assets resolve. Generate references before these non-mutating checks. |
| No unintended old names | Planned `python3 scripts/check_rename.py` and `python3 scripts/check_rename.py site`; documented narrow compatibility/history exceptions only. Regression-test this audit in `tests/test_rename.py`, including hidden tracked files and a forbidden old name in ordinary docs. Review every reported match. |
| Public-content and diff hygiene | `python3 scripts/check_public_content.py --history`; `python3 scripts/check_public_content.py site`; `git diff --check`. No credentials, private identifiers, or machine paths in deliverables. Planning files contain relative paths and the approved public issue URL only. |
| Native-host and visual confirmation | Run `python3 scripts/host_smoke.py` only with its isolated homes and non-generating checks. Inspect native plugin discovery output where supported; inspect renamed docs header, help, desktop/mobile labels, and social card. Record unavailable host inspection as a specific remaining check, never as a pass. |

The full suite is run once after targeted fixes, and repeated only for subsequent
changes or failures. The rename audit and full public-content scan have different
purposes. No generated-by trailers are added to commits.

## Deferred scope and limits

- Docs redesign, new logo geometry, fonts, tokens, layout, and app work are separate
  issues. This issue changes words and identifiers only.
- No GitHub repository/domain rename, redirect deployment, release publication,
  marketplace account action, real installation, or real host cache edits.
- No removal of aliases before 1.0. Record the planned removal in release notes;
  do not make runtime compatibility expire based on the current calendar date.
- No running-task migration or automatic edits to approved historical plan/model
  snapshots. Finish/cancel tasks before upgrade; use the existing rebind process
  for a deliberately resumed task after reviewing changed paths.
- No broad import compatibility layer or unrelated installer/runtime refactor.
  Compatibility code is limited to old entry names, project paths, managed
  markers, environment input, package selection, and receipt-owned state.
- Existing old product names in Git commit history remain historical facts.
  The name audit applies to deliverables, not rewritten Git history.

## Model evaluation and approval

Run the offline evaluator once using `facts.json`; `test_files` and `test_lines`
are estimates for six touched regression modules and roughly 400 new test lines.
This task merits demanding implementation/review and test-authoring routes because
of filesystem migration, bootstrap changes, and compatibility risk. Record the
actual result in `model-selection.json`; do not switch the active session or
silently configure unavailable models. A detached pipeline would require resolved
routes and a separately prepared manifest; it is not selected here.

Observed evaluator result: no model catalogue or configured routes were available
for any selected stage. The saved snapshot records this accurately. Continue in
the active Codex session after approval; no provider/model switch is selected.
The in-session lane does not use `validate-plan` or runner `preflight`, which
require a detached manifest. Planning verification consists of JSON validity,
requirements/check coverage, scope review, public-content scan, and diff hygiene.
No implementation tests or migration have been run during specification.

Approve this plan and start implementation?
