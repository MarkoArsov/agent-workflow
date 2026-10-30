---
name: project-setup
description: Detect repositories and conventions, confirm missing choices, and configure a customizable project workflow.
---

<!-- resolver:start -->
First run this skill folder's scripts/resolve.py from the active project. If it returns a project override, follow that file instead. Otherwise continue below.
<!-- resolver:end -->

# Set up a project

Use this for a new project, a changed repository layout, or a deliberate update to workflow preferences. The project can be a single repository or a non-Git folder containing several repositories.

1. Locate the bundled bin/plovi launcher relative to this skill's package. Run its setup command for the intended project root. It reads facts and prints a proposal; it does not apply changes.
2. Read existing project instructions. Explain detected repositories, roles, commands, branch/worktree conventions, delivery, and integrations, citing the detector's evidence. Distinguish findings from suggestions.
3. Ask only for missing consequential choices. Repository roles do not prove branch policies. Confirm which repositories participate always, when changed, or never; an unchanged E2E repo may supply checks without getting a task branch.
4. Confirm agents and whether to inherit machine model defaults or pin exact project routes and fallbacks. Use models inspect to show inherited settings; offer update-models if unconfigured. Leaving pipeline.routes empty permits adaptive selection during specify; existing explicit routes remain pins. Interactive execution follows the profile; trusted mode uses provider permission-bypass flags. Detached/non-TTY runs default to restricted unless reviewed policy or --trusted opts in to trusted execution. Save the profile choice once.
5. Put answers in a temporary JSON file with a profile object containing selected overrides and confirmed_defaults set to true only after the user has confirmed the proposed defaults. Resolve reported merge conflicts explicitly. Re-run setup with --answers and --output to produce the complete proposal.
6. Show the operating summary and proposed file changes. Include profile location, plan location, rules/references, connector settings, and every host adapter or instruction edit. Wait for approval of those changes.
7. Run setup --apply on that proposal with --approve and its exact digest. A stale proposal must be regenerated and shown again. Do not manufacture approval or apply a different proposal.
8. Run inspect, explain how to start specify, and show how to customize this project's skills. A route left unconfigured means the orchestrator is not ready; say what remains.

Re-running setup preserves manual settings, unknown extension keys, deleted optional values, and prose. Never edit installer-owned skills to customize a project. Use skill copy for a bundled override or skill new for a new project skill, then refresh discovery.

Keep credentials in the host's authentication system or referenced environment variables. Connector availability must be checked for each selected agent, including detached sessions. Show any host configuration patch before applying it.

Do not create task branches, install dependencies, run detected repository commands, start a pipeline, or post tracker updates as part of setup. Those actions have their own workflows.



New writable repositories default to worktree, regardless of observed Git history.
Offer a reviewed per-repository feature-branch or current-checkout choice for
new tasks; unmarked legacy profiles keep isolated worktrees. Setup
never creates task branches. Include planning.commit_plans (boolean, default true)
in the proposal and approval digest. Preserve explicit checkout/commit opt-outs
on repeat setup. For an unversioned multi-repository plan store, resolve an explicit
plan-owning configuration repository or planning.commit_plans=false before approval.
Do not initialize a Git parent. Identify untouched legacy defaults from generation
baselines before proposing migration; preserve ambiguous existing choices.

Show the commented plovi.toml proposal, effective limits and unattended permissions.
Interactive execution follows the profile; detached/non-TTY runs default to
restricted unless reviewed policy or --trusted selects trusted. Re-setup preserves
policy bytes and comments. Never silently activate policy for an existing run.
