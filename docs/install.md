---
title: Install
description: Install plovi with one command, then set up your project.
footer: docs
footer_order: 1
question: How do I install plovi?
---

# Install

!!! summary "In one minute"
    - **Mac:** paste one command into Terminal. **Windows:** paste one command into PowerShell.
    - Then open your project folder and start setup with `claude "/plovi-setup"` (or the Codex or Cursor equivalent).
    - You need Python 3.11 or newer, Git, and Claude Code, Codex, or Cursor.

## Before you start

You need three things. If you already have them, skip ahead.

| You need | Check it's installed | Get it |
|---|---|---|
| Python 3.11 or newer | Mac: `python3 --version`<br>Windows: `py --version` | [python.org](https://www.python.org/downloads/) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| An agent | `claude --version`, `codex --version`, or `agent --version` | Claude Code, Codex, or Cursor's CLI |

On Windows, when you install Python, keep **Add python.exe to PATH** checked.

## Install on Mac

**1.** Open **Terminal**: press Command-Space, type *Terminal*, and press Enter.

**2.** Paste this command and press Enter:

~~~sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh
~~~

**3.** If the output says *Add … to your PATH*, run the line it shows, then open a new Terminal window.

Linux works the same way: run the command in your terminal.

## Install on Windows

**1.** Open **PowerShell**: press the Windows key, type *PowerShell*, and press Enter.

**2.** Paste this command and press Enter:

~~~powershell
irm https://agentic.markoarsov.com/install.ps1 | iex
~~~

**3.** Close PowerShell and open a new window, so it finds the `plovi` command.

## Check that it worked

In a new terminal window, run:

~~~sh
plovi --version
~~~

It prints a version number, such as `0.1.1`.
The installer also added the `plovi-*` skills to each agent it found on your computer.

## Start using it

Go to your project folder, then start your agent with the setup skill:

~~~sh
cd path/to/your-project
claude "/plovi-setup"
~~~

| Agent | Run from your project folder |
|---|---|
| Claude Code | `claude "/plovi-setup"` |
| Codex | `codex "Use the plovi-setup skill"` |
| Cursor | `agent "Use the plovi-setup skill"` |

Setup reads your repository, asks a few questions, and shows every file it would write. Nothing is written until you approve. See [set up your project](setup.md).

Then describe your first change with `plovi-specify`, confirm the plan, and run `plovi-implement`. [Your first task](first-task.md) walks through it.

If your agent is already open, type `/plovi-setup` in Claude Code, or ask Codex or Cursor to use the `plovi-setup` skill. Its full name, `plovi-project-setup`, also works.

## If something goes wrong

| Message | What to do |
|---|---|
| *Python 3.11 or newer is required* | Install Python from [python.org](https://www.python.org/downloads/), open a new terminal, and run the install command again. |
| *Git is required* | Install Git from [git-scm.com](https://git-scm.com/downloads), open a new terminal, and run the install command again. |
| `plovi: command not found` (Mac) | Run the *export PATH* line the installer printed, then open a new Terminal window. |
| *plovi is not recognized* (Windows) | Open a new PowerShell window. The installer added the command to your PATH, but windows that were already open don't see it. |
| *running scripts is disabled* (Windows) | Use the exact install command above. It runs without changing your script policy. |

## Other ways to install

<details class="more" markdown>
<summary>Into one project instead of your user account</summary>

~~~sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh -s -- --project .
~~~
~~~powershell
& ([scriptblock]::Create((irm https://agentic.markoarsov.com/install.ps1))) --project .
~~~
The project gets its own copy at `.plovi/bin/plovi`, ignored by Git.

</details>
<details class="more" markdown>
<summary>Choose agents, or pin a version</summary>

~~~sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh -s -- --agents claude codex
curl -fsSL https://agentic.markoarsov.com/install.sh | PLOVI_REF=v0.1.1 sh
~~~
On Windows, pass options the same way as the project install above, and pin with `$env:PLOVI_REF = "v0.1.1"` before running the installer.

</details>
<details class="more" markdown>
<summary>From a clone, without the script</summary>

~~~sh
git clone https://github.com/MarkoArsov/agent-workflow.git
python3 agent-workflow/install.py   # on Windows: py agent-workflow\install.py
~~~
Add `--project /path/to/project` to install into one project, or `--json` for machine-readable output.

</details>
<details class="more" markdown>
<summary>Claude Code plugin</summary>

~~~sh
claude plugin marketplace add MarkoArsov/agent-workflow
claude plugin install plovi@plovi
~~~
The plugin contains the same skills and runtime; its skills are named `plovi:plovi-project-setup` and so on.
Use either the plugin or the installer for Claude Code, not both, to avoid duplicate skills.

</details>

## Before you run it

The scripts are short and readable: [install.sh](https://github.com/MarkoArsov/agent-workflow/blob/main/install.sh) and [install.ps1](https://github.com/MarkoArsov/agent-workflow/blob/main/install.ps1). They reject unsafe archive paths and verify the staged payload before switching versions; they do not verify a publisher signature.
plovi was previously named Scorebook. The GitHub repository still uses its original name, agent-workflow.

To update or remove it later, see [update and remove](lifecycle.md).

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
uses `plovi`; `discovery.aliases` can rename individual entry points. Change these values and
sync to replace the old owned entry points. Display-name changes do not move storage. Pre-rename linked installations retain their
existing receipt and settings directory while discovery and the launcher adopt the new name. If you move the checkout itself,
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

## Upgrade to plovi

### What changes for your workflow

Reinstall with `install.sh` or `install.ps1`, then use `plovi` and
`/plovi-<skill>`. Until 1.0, `agentflow` and `/af-<skill>` remain working aliases
and print a one-line deprecation note. The native Claude plugin qualifies the
same entries as `/plovi:plovi-<skill>` and `/plovi:af-<skill>`.

Finish or cancel running tasks before upgrading. On the first normal run of the
new runtime, an existing `.agentflow/` project directory moves to `.plovi/`.
User files and configuration stay intact, known configuration paths are rebased,
and a notice appears once. Preview commands report the pending migration without
changing files. If both directories exist, or either configuration directory is
a symlink, plovi stops: preserve both trees, compare their contents, and resolve
the conflicting configuration before retrying. It never merges them automatically.

Interrupted migrations keep a local recovery journal and resume on the next run.
If metadata changed outside plovi during recovery, preserve the journal and both
versions of the edit; resolve that edit before retrying. Do not remove the journal
to bypass a recovery error. Completed run evidence and approved snapshots are
preserved; a deliberate resume still needs the usual reviewed rebind.

Global installation receipts and model settings in a legacy data directory remain
in use; plovi does not move machine-wide configuration automatically. Projects
pinned to an older installed runtime keep selecting that runtime until you upgrade
the pin; migration happens when the project starts using the new runtime. Version
0.1.1 gives the renamed payload a distinct immutable version, so reinstalling does
not overwrite an existing 0.1.0 payload.

For the native Claude plugin, use its supported uninstall/install commands to
replace the former plugin with `plovi@plovi`; do not edit plugin caches. Restart
the host after reinstalling so its discovery list refreshes. The repository URL
and documentation domain stay the same.
