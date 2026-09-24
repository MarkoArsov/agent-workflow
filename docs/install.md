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
Open your project in the agent and invoke **aw-project-setup**.
Continue with [setup](setup.md).

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
