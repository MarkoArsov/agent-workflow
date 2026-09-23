# agent-workflow implementation plan

Status: Approved; Phase 3 implementation in progress.
License: MIT.
Delivery: a new public repository, developed and committed locally first.
The runner is a core feature. Project setup and customization make it reusable.

## 1. Product contract and accepted decisions

A user can install once on a machine, or install directly into a project folder.
A project is either one Git repository or a folder containing multiple repositories.
After invoking the setup skill, the user receives a working configuration for their
repositories, commands, delivery process, agents, and integrations. Each project can
then modify bundled skills, add skills and stages, define rules, and connect tools
without editing the installed package or affecting another project.

Accepted decisions:

- Support Claude Code, Codex, and Cursor, including headless runner adapters.
- Provide a portable installer and a Claude Code plugin/marketplace, using one
  canonical set of skills and runtime code.
- Make the existing trusted/unattended execution behavior the setup default.
  Codex uses `--dangerously-bypass-approvals-and-sandbox` in this mode.
  Setup explains and records the choice; restricted execution is configurable.
- Keep the manual `specify -> implement` lane alongside the full runner.
- Use tracked `ai-plans/<task>/` by default in a single repository. Store shared
  multi-repository plans at the configured project root. Ignore runtime evidence.
- Include GitHub PRs, Issues, and Actions; optional Linear and Notion connectors;
  CodeRabbit/Bugbot handling; and operation without an issue tracker.
- Replace forced promotion of repeatedly violated prose rules with a corrective
  review: automate what can be checked reliably, improve guidance otherwise.
- Build a polished, minimal MkDocs site on standard GitHub Pages first.
  A custom domain can be added later without rebuilding the documentation system.
- Keep dependencies small: Python standard library for installation and runtime,
  small POSIX launchers, Git, selected provider CLIs, and optional integration tools.
  MkDocs is a documentation development/build dependency only.

Existing workflow sources and handbook exports remain read-only. Their private
paths and source-specific comparison table stay outside this public repository.
Private templates and third-party skill bodies are not copied into this package.

## 2. Phase boundaries and progress

- [x] Phase 1: discover sources, compare active workflow files, agree port decisions.
- [x] Phase 2: record the complete implementation and verification plan.
- [x] Approval of this plan before any Phase 3 implementation.
- [ ] Phase 3.1: repository skeleton and shared contracts.
- [ ] Phase 3.2: project setup and customization, with fixtures.
- [ ] Phase 3.3: generic skills, runner, and integrations.
- [ ] Phase 3.4: installer, host adapters, and Claude plugin packaging.
- [ ] Phase 3.5: documentation website.
- [ ] Phase 3.6: root README and contribution guidance.
- [ ] Phase 4: full verification and public-content review.
- [ ] Phase 5: local handoff with exact publication instructions.

Update this checklist and a concise evidence log as work completes. A checkbox
requires observed evidence; test plans and mocks are not live-provider results.
Phase 2 ends with PLAN.md and a local planning commit only. No build starts until
the user approves it. Do not create a remote, push, publish, change GitHub settings,
or trigger deployment during this local task.

## 3. Repository layout

```text
agent-workflow/
  PLAN.md
  README.md
  LICENSE
  AGENTS.md
  CLAUDE.md
  pyproject.toml
  install.sh
  install.py
  bin/agent-workflow
  skills/<skill>/SKILL.md
  skills/<skill>/references/...
  references/...
  runtime/agent_workflow/
    cli.py
    project.py
    setup.py
    profile.py
    extensions.py
    install.py
    git_ops.py
    manifest.py
    runner.py
    state.py
    verification.py
    rules.py
    providers/{codex,claude,cursor}.py
    integrations/...
  schemas/{project,pipeline,stage,rule,connector}.schema.json
  templates/{project,instructions,adapters}/...
  .claude-plugin/{plugin,marketplace}.json
  scripts/{generate_docs,check_links,check_public_content}.py
  tests/
    fixtures/{single-repo,multi-repo}/...
    test_setup.py
    test_extensions.py
    test_install.py
    test_resolution.py
    test_runner.py
    test_git_ops.py
    test_integrations.py
  docs/
  mkdocs.yml
  requirements-docs.txt
  .github/workflows/{verify,pages}.yml
```

Names can be adjusted to keep implementation coherent, without changing contracts.
Schemas document the wire format; runtime validation uses a deliberately small
stdlib implementation for the supported formats, not a new general schema engine.
Use Python 3.11+ as the initial baseline and test supported interpreter versions.
Run the package from its installation root without requiring a global pip install.

The repository root is also the self-contained Claude plugin payload, including
runtime and shared references. The marketplace points to that payload. Host
wrappers and reference pages are generated from canonical sources; private source
trees, user profiles, and runtime logs are never packaging inputs.

## 4. Package, project, and repository boundaries

Keep these locations distinct:

| Root | Responsibility |
|---|---|
| Package root | Versioned, installer-owned skills, scripts, templates, and runtime. |
| Project root | Profile, custom skills/rules/connectors, shared plans, and project state. |
| Repository root | One registered Git repository with its own base, commands, and role. |
| Task checkout | Current checkout or task worktree for one participating repository. |

Project-owned layout:

```text
<project>/
  PROJECT_WORKFLOW.md
  .agent-workflow/
    project.json
    package-lock.json
    skills/<name>/SKILL.md
    rules/...
    references/...
    connectors/...
    stages.json
    overrides.lock.json
    runtime/                 # ignored, project installations only
    local/                   # ignored: receipts, baselines, registry, evidence
  ai-plans/<task>/
  <registered-repositories>/
```

Only create optional extension directories when used. A single-repository project
uses `.` as its repository path. A multi-repository parent need not be a Git repo.
If that parent is unversioned, setup says explicitly that its shared configuration
and plans are durable local files. It can use a user-selected configuration repo;
it never initializes a Git repository around existing children without instruction.

Each child repository receives an approved, small relative project reference and
the host discovery adapters it needs. Worktree references are resolved through Git
metadata and an explicit project registration. Do not infer membership from a
directory's name or a hard-coded path on a particular developer's machine.

Resolution order:

1. An explicit project argument, validated against the active repository.
2. A project reference attached to the repository or its registered worktree.
3. The nearest ancestor profile that explicitly lists this repository.
4. A user-level registration with an unambiguous matching Git common directory.
5. No match: invoke setup or request the missing project choice.

An unrelated parent profile must not absorb a nested repository. Resolve symlinks,
spaces, moved folders, nested working directories, and Git worktrees consistently.
Repository references must remain portable; machine-specific absolute registrations
belong in ignored local state.

## 5. Project setup

### Detection

The setup skill invokes a read-only scanner. It inspects existing instructions,
Git metadata, manifests, lockfiles, task/build files, CI configuration, PR templates,
review-bot configuration, and existing workflow configuration. It does not execute
commands discovered in repository files or contact a tracker just to guess defaults.

Report each finding with its source and confidence:

- Candidate repositories, their roles and relationships, and generated/worktree
  checkouts that should not be registered twice.
- Languages and stack markers: Python, Node, .NET, Go, Rust, and generic Make/Task
  commands. Unsupported stacks can supply explicit commands.
- Build/test/lint/format commands per repository, with working directory and order.
- Current/default branches, remote roles, recent branch/commit conventions, and
  established worktree usage. History suggests preferences; it does not authorize them.
- PR flow, CI provider, review bots, issue tracker, existing connector availability,
  and native host instructions.
- Configuration ownership, plan location, and current user edits on re-setup.

Exclude dependency trees, caches, runtime logs, credential files, and secret values.
Read connector configuration structure only as needed and redact sensitive fields.

### Interview and confirmation

Ask only about unresolved choices. Repository role alone cannot determine branch
policy or task membership. Confirm `always`, `when-changed`, or `never` task
participation and `current-checkout`, `feature-branch`, or `worktree` strategy.
A repository may be readable for tests without being writable for the task.

Show one reviewable summary and proposed file diff before writing. It covers
repository membership, commands, branches, plan storage, selected agents, routes,
permissions, connectors, and all instruction/adapter updates. Confirmation applies
to that exact proposal, not to unseen future discoveries.

Recommend trusted/unattended execution as the default requested for this product.
Explain it once in setup, record it, and reuse it. Do not repeat permission interviews
on each task. Do not infer permission to comment, message, or change tracker state
from the provider's process-level permission setting.

### Profile schema

The profile is versioned JSON with stable repository and command IDs. This abbreviated
example shows the structure; setup fills the actual detected values and confirmed
routes. An empty route map is allowed before configuration, but cannot start a run.

```json
{
  "schema_version": 1,
  "project": {
    "id": "sample-workspace",
    "kind": "multi-repo",
    "configuration_root": "."
  },
  "package": { "version": "0.1.0" },
  "agents": ["claude", "codex", "cursor"],
  "repositories": [
    {
      "id": "app",
      "path": "app",
      "roles": ["application"],
      "base_branch": "main",
      "remote": "origin",
      "task_policy": "when-changed",
      "checkout_strategy": "worktree",
      "commands": {
        "test": {
          "argv": ["python3", "-m", "unittest", "discover"],
          "cwd": ".",
          "parser": "unittest",
          "timeout_seconds": 300
        }
      }
    },
    {
      "id": "checks",
      "path": "checks",
      "roles": ["e2e"],
      "base_branch": "main",
      "remote": "origin",
      "task_policy": "when-changed",
      "checkout_strategy": "worktree",
      "commands": {}
    }
  ],
  "planning": {
    "directory": "ai-plans",
    "evidence_directory": ".agent-workflow/local/evidence"
  },
  "git": {
    "branch_template": "feature/{task}",
    "commit_style": "imperative",
    "worktree_directory": ".agent-workflow/local/worktrees"
  },
  "delivery": {
    "pull_requests": "draft",
    "publish": "plan-selected",
    "merge_to_base": "explicit"
  },
  "tracking": { "provider": "none" },
  "execution": {
    "permission_mode": "trusted",
    "provider_settings": {}
  },
  "pipeline": {
    "enabled": true,
    "default_stages": [
      "implement-tests", "implement", "review", "commit-and-push", "draft-pr"
    ],
    "routes": {}
  },
  "extensions": {
    "skills": ".agent-workflow/skills",
    "rules": ".agent-workflow/rules",
    "references": ".agent-workflow/references",
    "connectors": ".agent-workflow/connectors",
    "stages": ".agent-workflow/stages.json"
  }
}
```

The full schema also defines validation policies, test/product paths, repository
dependencies, optional service lifecycle commands, branch alignment, per-stage model
and reasoning choices, approved fallbacks, review bots, and connector references.
Commands use argv arrays; shell execution must be an explicitly configured command.
Credentials are references to environment variables or existing host authentication,
never values in the profile. Draft PR delivery is configurable, including no PR flow.

Project defaults are inherited by a task manifest, which records the final selected
repositories, stages, routes, permissions, commands, and scope. Do not silently run
every default stage or attach every repository to every task.

### Generated outputs and re-runs

Generate the profile, concise PROJECT_WORKFLOW.md, necessary project references and
host adapters, and scoped guidance only where repository evidence justifies it.
Create project-specific E2E/environment references when required. Never fork every
generic skill just because setup ran.

Preserve existing AGENTS.md, CLAUDE.md, host settings, and ignore files. Add only
approved managed blocks or individual owned entries, with conflict detection.

Re-setup is a three-way comparison of the previous generated baseline, current user
content, and new detection results. Merge objects by key and repository/command lists
by stable ID. Preserve user deletions, unknown extension keys, and manual prose.
Conflicting changes require a displayed choice; do not resolve them by overwriting.

An unchanged run preserves file bytes. Apply approved changes atomically where
possible, keep recoverable local backups, and roll back partial multi-file failures.
Record ownership and baseline hashes in local state. Detection caches and backups
are excluded from version control and distribution.

## 6. Project customization and updates

Customization is a shipped user journey, not an advanced undocumented escape hatch.

| User action | Supported mechanism |
|---|---|
| Change a bundled skill | Copy it into the project skill directory and edit it. Record its base package version/hash. |
| Add a skill | Add a valid skill folder and refresh host discovery. The runner uses the same catalog. |
| Add scoped guidance | Project references or path-scoped rules, loaded for relevant stages only. |
| Add an enforced convention | Rule metadata and an approved detector or warning; generic neutral examples ship with the package. |
| Connect another service | Add a connector declaration and configure its host adapter or command transport. |
| Change the sequence | Enable/disable optional stages and register named project stages with explicit contracts. |
| Share the workflow | Commit project-owned configuration and extensions, with portable references and no credentials. |

Skill resolution is project override, then the selected package's bundled skill.
Local rule/reference selection is explicit and scoped. Nearby native project
instructions and current user instructions retain their authority.

New and modified skills are used in both direct invocation and detached stages.
Provide CLI helpers for copying a bundled skill, creating a new one, listing effective
sources, validating extensions, and refreshing host adapters. Host discovery adapters
are disposable generated files; project skill bodies are user-owned.

A project stage declares its name, skill or command, required inputs, permitted
outputs, completion verifier, and position in an ordered pipeline. Validate dependency
ordering: built-in publication still requires current implementation verification.
Custom stages can extend the flow without editing the installed runner. Do not build
an unrelated general-purpose DAG service.

Updates never replace project-owned skills, rules, references, or connector content.
Report upstream changes to overridden skills and offer a reviewable refresh/merge.
Do not silently apply upstream changes to an override. Keep a single effective source
for each skill and show its origin in `agent-workflow inspect`.

At run start, record the package version and hashes of the effective profile, skill
bodies, rules, references, and stage definitions. Keep that snapshot for the run.
Updates affect a subsequent run; a deliberate rebind/resume records changed inputs
and invalidates affected downstream evidence.

## 7. Runner and verification contracts

The default full sequence is:

```text
implement-tests? -> implement -> review? -> commit-and-push? -> draft-pr?
```

The runner must be complete and usable, not a script that only prints prompts.

- `specify` writes the complete approved plan: prompt, product requirements,
  implementation approach, deferred scope, and a validated pipeline manifest.
- The manual lane needs a concise plan and in-session checks without detached stages.
- Test changes in the full lane use independent test authoring and assertion-level
  red evidence. Compile errors, missing imports, and broken setup are not red proof.
- Implementation owns product changes and the full named verify/fix procedure.
- Every planned outcome maps to an observed check. Test parsers cover common formats
  and an explicit generic success/failure matcher. Documentation-only changes can use
  link/build checks instead of invented product tests.
- Evidence includes exit status, output, test identity, affected paths, and a diff
  fingerprint. An agent saying "passed" is insufficient.
- Review starts fresh, sees requirements and the actual diff, and does not receive
  implementation reasoning. Direct review is check-only. Pipeline review may make
  safe in-scope corrections and verifies affected checks. Review findings are advisory;
  deterministic path, secret, convention, and publish guards remain blocking.
- Fixes during review or custom stages invalidate evidence for affected changes;
  publish cannot reuse results from a different diff without justified revalidation.
- Scripts own commit/push/draft PR mechanics, preserve conventions, and operate only
  on participating repositories. No force pushes, base-branch pushes, or surprise merges.
- Independent repositories are not a distributed transaction. On partial delivery,
  record per-repository commit/push/PR state and resume without duplicating actions.
- Plan revisions preserve audit history and rebind to a complete revision, invalidating
  the necessary downstream state rather than discarding unrelated completed work.
- Bound retries and recovery. Permanent authentication/quota/model failures advance
  only through approved fallbacks. Genuine input requests resume the exact asking
  provider/session; retries and route changes start fresh sessions.
- Provide dry-run, preflight, detached execution, status, watch, resume, answer, and
  cancellation. Enforce a project/task lock and manage only owned child processes.
- Preserve valid interrupted test/implementation evidence after rechecking its inputs.
  Detect inactivity and stalled inner tools; do not retry forever.
- Keep prompt prefixes stable where context contracts permit and append changing run
  information separately. Token/cost fields are reported only when providers expose
  them; unknown cost is not zero and usage is not fabricated.
- Shared local test environments use configured ownership/locks, cleanup, and bounded
  recovery. Unchanged test repositories remain untouched.

Provider adapters construct both initial and resume commands. Trusted mode uses the
current validated bypass flags for each installed provider. Restricted mode uses
supported provider controls, reports differences, and stops preflight if the requested
boundary cannot be honored. It never silently falls back to trusted mode.

No provider is mandatory for all stages. Setup discovers available CLIs and records
user-selected models, reasoning, and fallbacks rather than baking volatile model IDs
into the generic workflow. Preflight verifies capability and model/flag compatibility.

Process permissions and plan contracts are different controls. In trusted mode,
path checks and sanitization verify outcomes; they are not an operating-system sandbox.
The audit reports actual configured access and observed provider behavior.

## 8. Approved capability migration

The private source-to-file map was approved during discovery. Public documentation
uses capability names and generic examples, not the original private identifiers.

| Capability | Implementation disposition |
|---|---|
| Setup/profile | Rebuild for explicit project membership, commands, ownership, and extensions. |
| Specification | Sole plan author, established-pattern research, two execution lanes. |
| Test authoring and implementation | Test-first evidence and in-session verify/fix. |
| Independent review | Direct and pipeline modes, scope-aware corrections and narrow verification. |
| Runner | Generalize manifest/state/context/recovery and evidence mechanisms. |
| Git and PR delivery | Consolidate draft-PR creation; configurable base/branch/commit/PR conventions. |
| Worktree utilities and base sync | Optional repository participation; use generic `sync-base`. |
| Comment handling and peer review | Human-selected fixes, bot adapters, pagination, factual reply drafts. |
| CI diagnosis | GitHub Actions first, pluggable project commands for other CI providers. |
| E2E authoring/overview/environment lifecycle | Fresh generic procedures plus setup-generated references. |
| Post-merge smoke checks | Configured environments, observed readiness, bounded actions and cleanup. |
| Rule capture and context maintenance | Three enforcement classes, repeat-violation review, proposal-only pruning. |
| Manual procedure helper | Optional guided setup/cutover artifacts with explicit side effects. |
| Direct merge and review request | Separately invoked, project-enabled; requests are drafts until authorized. |
| Tutoring, review walkthrough, RFC drafting | Fresh generic optional skills. |
| Issue drafting/tracking and PR preflight | Fresh provider-neutral equivalents; GitHub/Linear/none support. |
| Code conventions | Learn project patterns rather than importing a private language rulebook. |
| Workflow inventory and maintenance | Generated catalog and project-aware customization guidance. |

Retain generic result classification and external-input sanitation, with tests.
Adapt all remaining useful runtime helpers and tests to the profile-driven layout.
Replace the old execution-profile runner and second planning skill.
Exclude private credential readers, infrastructure recipes, historical task material,
company convention examples, IDE process management, and private package synchronization.
Use public package update/uninstall in place of private-source update utilities.

The public site is generated from approved package documentation and skills only.
It must never read local task status, run history, profiles, logs, or private sources.

## 9. Integrations and authorization

Ship capability declarations and adapters, not assumed universal tool names.

- GitHub: use the authenticated GitHub CLI for PRs, Issues, checks, and Actions evidence.
  Repositories come from the project profile. Paginate full comment/thread retrieval.
- Linear and Notion: support available MCP/host connectors and project-defined command
  adapters. Credentials stay with the host or referenced environment. Missing access
  has a concrete setup/preflight message and a supported Markdown/no-tracker path.
- CodeRabbit and Bugbot: detect bot identity/configuration, retain bounded review rounds,
  and restore draft state when an explicitly requested bot flow temporarily changes it.
  Never post bot-control comments or resolve threads implicitly.
- Custom connectors: declare transport, executable/endpoint reference, capabilities,
  authentication requirements, and which agents/stages use it. Preserve unrelated
  host configuration when applying an approved connector patch.

Connectors available in one interactive host may not exist in another headless CLI.
Check availability per selected route. Never claim a connector works across all agents
because it works in the setup session.

Reads and local drafts follow the requested task. Comments, messages, issue creation,
tracker changes, and review actions require authorization for that action and content.
Selecting commit/push/draft-PR stages authorizes those named delivery actions only.

## 10. Installation, precedence, update, and removal

### Distribution comparison and selection

A Claude-only plugin offers native discovery/lifecycle but does not meet the complete
cross-agent project-resolution requirement. A standalone installer meets that requirement
but lacks native Claude distribution. Ship both over the same payload.

The POSIX bootstrap downloads a pinned package revision into a temporary directory,
validates archive paths and package integrity, and invokes the stdlib Python installer.
It supports a local source checkout for development and offline fixture testing.
Do not require Node, a daemon, a package registry account, or an installer dependency.

After the repository is published, the README will provide one command per mode.
The following are planned interfaces, not commands to execute during this local task:

```sh
curl -fsSL https://raw.githubusercontent.com/<owner>/agent-workflow/<ref>/install.sh | sh -s -- --global
curl -fsSL https://raw.githubusercontent.com/<owner>/agent-workflow/<ref>/install.sh | sh -s -- --project /path/to/project
```

The project path can be a single Git repository or a parent folder. A pinned tag or
commit replaces `<ref>` in the release instructions. A downloaded installer remains
executable code; package checksums are not represented as independent signatures.

### Installation locations

- Global: versioned payload under `~/.local/share/agent-workflow/`, a user CLI shim,
  and installer-owned host discovery entries. Respect supported XDG/config overrides.
- Project: payload under `<project>/.agent-workflow/runtime/`, with a local launcher
  and project/child-repository discovery entries. It works without a global install.
- Both modes record ownership, package version, active paths, and installation backend.
  Installation enables setup; it does not infer and write a project operating profile.

A project-owned runtime has priority over a global runtime. A project's package lock
pins the version. Resolve a matching local/global version or the invoked plugin's
bundled version; report a missing required version rather than silently mixing versions.
Uninstalling the project package permits fallback to a compatible global package.

Global and project discovery wrappers use the same resolver. Use namespaced `aw-*`
standalone entry points to avoid overwriting unrelated skills. Claude plugin invocation
uses its plugin namespace. Do not rely on host duplicate-name behavior for precedence.
For Codex and Cursor, prefer shared documented `.agents/skills` discovery; Claude
standalone adapters use its skills directory. Generate additional host adapters only
where required. Native plugin and standalone entry points must resolve the same project
overrides and package version. Detect duplicate backend installations and report ownership.

Project-local plugin scope and a shared multi-repository parent require explicit
child-repository discovery; native plugin scope alone does not define project membership.
Keep plugin paths within the distributed payload so cache relocation remains valid.
New project skills are registered by the common refresh command for each selected host.

### Update and uninstall

Provide `agent-workflow update`, `uninstall`, `inspect`, and `doctor` with explicit
global/project targets and dry-run output. Dispatch native plugin lifecycle operations
through its supported CLI; do not hand-edit plugin caches.

Stage updates, validate compatibility, then switch versions atomically. In-use snapshots
remain valid. Preserve custom files and show conflicts in modified installer-owned files.
Remove only receipt-owned, unchanged files on uninstall. Leave user profiles, skills,
rules, plans, and connectors intact; restore any previously backed-up owned configuration.
Never recursively remove a shared host skill directory or modify another project's install.

Document macOS prerequisites. Test the portable core on Linux and explain any host-specific
differences. Offer WSL as the initial Windows path; native Windows process groups,
launchers, path handling, and host discovery are a documented follow-up, not claimed support.

## 11. Documentation and visual design

Use MkDocs with a built-in theme and a small local CSS override. Keep documentation
sources readable as Markdown. Avoid a large theme/plugin dependency chain or remote
analytics, font, and script dependencies.

Visual goals: clear typography, restrained color, generous spacing, readable code and
tables, obvious navigation, accessible contrast, responsive layouts, and useful search.
Use a concise landing page with the install -> setup -> run path. Put advanced details
on their own pages and keep implementation internals out of onboarding.

| Navigation group | Pages |
|---|---|
| Start | Overview/principles; quick setup; installation; update/uninstall. |
| Configure | Setup skill; single/multi-repository projects; profile reference; commands and permissions. |
| Use | Task lifecycle; manual/full pipeline; review and everyday use; generated skill reference. |
| Customize | Modify/add skills; rules/references; custom stages; connectors; sharing project configuration. |
| Verify | Verification checkpoints; current coverage and limitations; post-merge checks. |
| Recover | Troubleshooting, failed stages, input pauses, resume, and partial delivery. |
| Maintain | Change the workflow safely; package development; model choice and cost controls. |

This preserves the source handbook's separation of overview, lifecycle, workspace map,
daily use, reference, recovery, maintenance, coverage, and model choices. Write new
public text and examples; do not reproduce company material or the unavailable chapter.

Generate reference pages from shipped SKILL.md files and schema descriptions through
a small build hook/script. Regenerate during both preview and build. CI detects stale
generated indexes and broken links. Public builds use an allowlisted source set.

Provide local preview and strict production build commands. Test project-subpath URLs,
internal pages, anchors, navigation, and static assets. GitHub Actions builds an artifact
and deploys through the official Pages workflow with minimal job permissions.
Commit the workflow locally; it is not run or enabled during this task.

The README includes a short pitch, both one-command installations, setup/run examples,
customization entry points, prerequisites, and the eventual site link. Keep detailed
reference material on the site. Use the standard Pages URL initially; later custom-domain
configuration is documented separately.

## 12. Verification and acceptance

Use stdlib unittest/subprocess and temporary workspaces for core tests. All installer,
setup, provider-double, and Git fixture tests run with an isolated child-process home
and isolated host configuration/cache paths. Construct this environment from an allowlist;
do not inherit credential variables. Do not alter the parent shell's home/config values.

Use task-specific variables for test directories. The child environment redirects HOME
and the relevant provider/XDG configuration paths. Mock provider and integration executables
prevent OS credential-store access and network calls during automated fixture tests.
Never install into or modify real user agent configuration while testing this package.

| Area | Required observed proof |
|---|---|
| Single-repository setup | Detect stack, commands, branch/PR choices; show proposal; write only after approval; resolve from a nested directory. |
| Multi-repository setup | Non-Git parent with an application repo and separate E2E repo; profile shared across both; app-only task does not branch or modify the unchanged E2E repo. |
| Fixture execution | Run actual fixture checks, including an E2E request to a disposable local application; prove failure then success where required. |
| Re-setup | Second identical run makes no byte changes; manual field/prose edits, deletions, and added skill/rule/connector survive detection changes. |
| Project isolation | Two projects using one global package can resolve different skill overrides, rules, connector choices, and stage sequences without cross-contamination. |
| Discovery | Nested paths, spaces, symlinks, child repos, moved profiles, and Git worktrees resolve; unrelated siblings/parents are rejected. |
| Install modes | Global-only, project-only in a repo, project-only in a non-Git parent, and both installed; project precedence verified. |
| Lifecycle | Update, reinstall, rollback on failure, conflict reporting, and uninstall preserve custom and unrelated host files; compatible global fallback works. |
| Plugin | Validate manifests and test payload relocation; native lifecycle in isolated config if supported; actual discovery/override behavior gets a host smoke check. |
| Customization | Modified built-in skill and newly added skill used by direct adapters and runner; custom stage runs; update preserves both. |
| Connectors | Add/disable/replace a project connector, preserve host settings, and diagnose per-provider absence; keep secrets out of generated files and logs. |
| Runner lifecycle | Fresh processes, exact-session input resume, configured fallback, permanent/transient failures, cancellation, locks, stalled tools, and interrupted evidence recovery. |
| Runner evidence | Reject setup failures as red proof, stale diff evidence, missing acceptance checks, out-of-scope writes, skipped tests, and false success markers. |
| Repository delivery | Local commits and bare temporary remotes verify participation, base/force-push guards, partial delivery resume, and clean parked checkouts. |
| Host commands | Initial and resume invocations for all three providers honor saved permission/model settings; unsupported modes fail clearly. |
| Rule recurrence | Repeated non-mechanical violations produce a corrective proposal without forcing a fictional detector; real blocking checks still fail. |
| Documentation | Strict build, preview, internal page/anchor/asset checks, generated references, and desktop/mobile visual inspection. |
| Public content | Scan tracked/untracked deliverables, names, symlink targets, generated site, release payload, and reachable commit content for private data. |

The main fixtures use small standard-library applications/checks to avoid requiring a
production stack. Add static manifest fixtures for other language detectors. Tests
create temporary Git repositories and local remotes; fixture source does not embed .git
directories, real project names, real tickets, or personal paths.

Simulated provider/connector tests must be labeled as such. Add bounded real-host smoke
checks where available, keeping them separate from isolated automated tests. Never use a
real account just to test publishing. If sign-in, native discovery, or a provider-specific
step cannot be automated, supply the exact manual procedure and expected outcome.

Public-content checks use an external private denylist supplied at verification time,
not a tracked file containing forbidden terms. Also scan generic secret/personal-path
patterns and perform a human-readable review; grep alone cannot prove safe provenance.
Do not copy private material temporarily into Git and remove it later. Check before
each commit, and report the final scan scope, findings, and any approved public metadata.

Normal Git author metadata uses the configured personal identity. Repository content
contains no real personal names, private identifiers, internal URLs, or machine paths.
Public repository/site URLs are filled with the approved owner's public handle.

## 13. Implementation order and evidence log

1. Skeleton: license, repository instructions, package entry points, schemas, test harness.
2. Setup: detector, confirmation/apply model, profile resolution, project extensions,
   re-run behavior, and both executable fixtures.
3. Port: generic skill set, runner/provider adapters, verification, Git operations,
   rules, and agreed integrations. Preserve working behavior before broad cleanup.
4. Install: bootstrap, both modes, ownership/receipts, discovery, plugin manifests,
   precedence, lifecycle, and extension-preserving updates.
5. Site: navigation, concise new content, generated references, styling, local preview,
   strict build, link checking, and Pages workflow.
6. README: shortest complete installation/setup/run/customization path and support matrix.
7. Verify and hand off: run the matrix, review public content/history, document actual
   deviations and remaining external/manual checks.

Commit logical chunks locally after their relevant checks, using the personal identity
resolved in the new repository. Never add generated-by or model attribution trailers.
No remote is added during the build. Keep unrelated source workspaces unchanged.

Evidence log at Phase 2: discovery and decisions completed; no implementation tests,
installation, provider runs, website build, or publication have been performed.

Implementation evidence (local, initial runtime milestone):

- Setup, project extension resolution, provider command construction, and runner
  verification: 19 isolated tests passed. Provider execution uses explicitly labeled
  local doubles, including exact-session input, fresh fallback, and stalled tools.
- Installer and executable fixtures: 8 tests passed with temporary homes/configuration.
  Global/project install, update rollback, override preservation, native payload
  relocation, and compatible global fallback are exercised.
- The multi-repository fixture made a real HTTP request to a disposable local app;
  its checks repository remained clean on its original branch and revision.
- Initial public-content scan: 130 filesystem/history items, zero findings with
  an external private denylist. No real provider generation or publication occurred.
- Git delivery, integration edge cases, website, schemas, and final verification
  remain in progress; this milestone is not the completed acceptance matrix.

## 14. Handoff and publication boundary

Deliver a concise report of what was built, plan deviations, observed verification,
limitations, remaining manual checks, local commit history, and repository location.

Provide exact commands, filled with the agreed owner and repository name, for:

1. Verifying personal Git identity and the personal SSH host alias.
2. Creating the public remote repository with the selected license already local.
3. Adding `git@github-personal:<owner>/agent-workflow.git`.
4. Pushing the approved local branch and any chosen release tag.
5. Enabling GitHub Pages with GitHub Actions.
6. Confirming the site URL and bootstrap install commands from the published revision.
7. Adding a custom domain later.

These remain a joint, later publication step. This task ends locally; no command
above is executed automatically.

## 15. Official compatibility references

Validate host-specific behavior against these references during implementation.
Local fixtures prove package behavior; vendor documentation is not a substitute for
a real-host smoke check.

- [Claude plugin creation](https://code.claude.com/docs/en/plugins)
- [Claude installation and scopes](https://code.claude.com/docs/en/discover-plugins)
- [Claude plugin reference](https://code.claude.com/docs/en/plugins-reference)
- [Codex skill discovery](https://learn.chatgpt.com/docs/build-skills)
- [Cursor skill discovery](https://cursor.com/docs/skills)
- [Cursor CLI permissions](https://cursor.com/docs/cli/reference/permissions)
- [MkDocs build and preview](https://www.mkdocs.org/getting-started/)
- [GitHub Pages Actions workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
