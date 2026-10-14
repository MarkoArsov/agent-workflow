---
description: Install Stagecoach globally or inside a project.
footer: docs
footer_order: 1
---

# Install

You need Python 3.11+, Git, and at least one authenticated agent CLI: Claude Code, Codex, or Cursor.
GitHub delivery also uses `gh`. The runtime has no Python package dependencies.

The CLI and package are still named `agent-workflow` while the rename is in progress.

macOS and Linux use the same installer. Use WSL on Windows; native Windows is not yet supported.

## Choose a scope

| Scope | Use it when |
|---|---|
| Global | You want one installation available across projects. |
| Project | You want a self-contained runtime inside one repository or a parent folder containing several. |

After the first release is published:

~~~sh
curl -fsSL https://raw.githubusercontent.com/MarkoArsov/agent-workflow/v0.1.0/install.sh | sh -s -- --global
~~~

Or install into an existing project folder:

~~~sh
curl -fsSL https://raw.githubusercontent.com/MarkoArsov/agent-workflow/v0.1.0/install.sh | sh -s -- --project .
~~~

These URLs require the matching published tag. Review the pinned script before running it if that is your normal installation policy.
The installer checks archive paths and staged payload integrity; it does not provide an independent publisher signature.

## From a checkout

This works before publication and without downloading a release:

~~~sh
python3 install.py --global
# Or:
python3 install.py --project /path/to/project
~~~

Use `--agents codex claude` to install only selected host entries.
Global commands live in `~/.local/bin`; add that directory to PATH if necessary.
A project install provides `.agent-workflow/bin/agent-workflow`.

Installation enables discovery. It does not write a project profile.
Open your project in the agent and invoke **af-setup**.
Skill labels use an uppercase **AF** prefix, such as **AF Setup** and **AF Specify**,
through generated display metadata. Invocation names remain lowercase (`af-setup`).
Continue with [setup](setup.md).

## Follow a development checkout

For a machine that should use every local edit immediately, link the global runtime:

~~~sh
python3 install.py --global --link
python3 install.py --global --sync
~~~

The first command registers this checkout without copying the runtime. Skills, scripts,
and references load from it on the next invocation, including uncommitted changes.
The second command reconciles discovery entries when skills are added, removed, renamed,
or their descriptions change. It does nothing when the installation is current.
Run it after edits, or schedule it locally. On macOS, a user LaunchAgent can run the
absolute Python and installer paths with `--global --sync`, `RunAtLoad`, and a
`StartInterval` of 30 seconds. Keep that machine-specific service outside this repo.

Public skill names come from `workflow-package.json`: `discovery.prefix` currently
uses `af`, and `discovery.aliases.project-setup` uses `setup`. Change these values and
sync to replace the old owned entry points. The package's internal identity and storage
paths remain stable across display-name changes. If you move the checkout itself,
rerun the link command from its new location and update your local scheduler's path.

A project with its own installed runtime keeps that pinned runtime. Other projects use
the linked runtime when its profile schema is compatible, even when its version changes.
Project overrides still take precedence. Setup uses global discovery for bundled skills
when this linked checkout covers the project's hosts, so future renames cannot leave stale
local copies. Custom project skills and existing project discovery files are refreshed
through the project's reviewed setup/refresh flow; global sync never rewrites projects.
Modified discovery files cause a conflict instead of being overwritten. Uninstall removes
owned discovery entries and leaves the source checkout intact. Remove any local scheduler
when you uninstall. Restart the host if its skill selector retains older names.

## Claude's native plugin

After publication, add the marketplace and install the plugin:

~~~sh
claude plugin marketplace add MarkoArsov/agent-workflow
claude plugin install agent-workflow@agent-workflow
~~~

Use **agent-workflow:project-setup**. The plugin contains the same skills and runtime.
You can inspect a checkout with `claude --plugin-dir .` before publication.

Choose one Claude discovery backend to avoid duplicate entry points.
A plugin scoped to one repository does not automatically configure sibling repositories; shared project setup creates the explicit references and adapters they need.
