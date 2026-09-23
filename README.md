# agent-workflow

A customizable development workflow for **Claude Code, Codex, and Cursor**.

Install once, set up a repository or a folder of repositories, and keep each project's skills, rules, connectors, and stages under your control. The runner starts fresh agent sessions and verifies their work with executable checks.

**Plan → tests → implement → review → deliver**, with a small manual lane when a full pipeline is unnecessary.

[Documentation](https://MarkoArsov.github.io/agent-workflow/) · [Local docs](docs/index.md) · [Coverage](docs/coverage.md) · [MIT license](LICENSE)

## Install

Requires Python 3.11+, Git, and an authenticated agent CLI. macOS/Linux; WSL for Windows.
GitHub delivery also requires the GitHub CLI. No runtime Python dependencies.

From this checkout:

~~~sh
python3 install.py --global
# Or install into a single repository or multi-repository parent:
python3 install.py --project /path/to/project
~~~

After the v0.1.0 release is published:

~~~sh
curl -fsSL https://raw.githubusercontent.com/MarkoArsov/agent-workflow/v0.1.0/install.sh | sh -s -- --global
curl -fsSL https://raw.githubusercontent.com/MarkoArsov/agent-workflow/v0.1.0/install.sh | sh -s -- --project .
~~~

Claude's native plugin uses the same payload:

~~~sh
claude plugin marketplace add MarkoArsov/agent-workflow
claude plugin install agent-workflow@agent-workflow
~~~

The remote commands require publication. Review the pinned bootstrap before executing it.

## Set up and run

1. Open your project in an agent and invoke **aw-project-setup** (native Claude: **agent-workflow:project-setup**).
2. Confirm repositories, commands, branch policies, models, permissions, and integrations. Review the complete proposal before it writes.
3. Invoke **aw-specify** for a task, then **aw-implement-pipeline** for the approved full plan—or use **aw-implement** directly for the manual lane.

~~~sh
agent-workflow preflight ai-plans/task-name/pipeline.json
agent-workflow run ai-plans/task-name/pipeline.json --detach
agent-workflow status task-name
~~~

A project install uses `.agent-workflow/bin/agent-workflow`; global installs use `~/.local/bin`.

Trusted unattended execution is the offered default, including Codex's
`--dangerously-bypass-approvals-and-sandbox`. Setup can select restricted controls instead.
Task scope and evidence guards remain in force. Comments, messages, and tracker changes need their own authorization.

## Make it yours

~~~sh
agent-workflow skill copy review
agent-workflow skill new release-notes --description "Draft release notes from verified changes."
agent-workflow refresh
~~~

Edit project-owned copies, review the discovery proposal, and apply it.
Add [rules](docs/rules.md), [custom stages](docs/customize.md), or [connectors](docs/connectors.md).
Updates preserve these extensions.

## What the runner verifies

- Named acceptance checks, behavioral red evidence, and green evidence for the current diff.
- Writable paths and repository participation, including unchanged test companions.
- Fresh stage/fallback sessions, exact-session input answers, bounded recovery, and cancellation.
- Guarded feature commits/pushes, draft PRs, and resumable partial delivery.
- Effective project skill overrides and declared custom-stage completion checks.

[Run the tests and build the docs](CONTRIBUTING.md). Provider doubles are labeled;
[real-host checks and limitations](docs/coverage.md) remain explicit.
