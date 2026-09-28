---
title: Install
description: Install Agent Flow with one command, then set up your project.
footer: docs
footer_order: 1
question: How do I install Agent Flow?
---

# Install

!!! summary "In one minute"
    - **Mac:** paste one command into Terminal. **Windows:** paste one command into PowerShell.
    - Then open your project folder and start setup with `claude "/af-setup"` (or the Codex or Cursor equivalent).
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

**3.** Close PowerShell and open a new window, so it finds the `agentflow` command.

## Check that it worked

In a new terminal window, run:

~~~sh
agentflow --version
~~~

It prints a version number, such as `0.1.0`.
The installer also added the `af-*` skills to each agent it found on your computer.

## Start using it

Go to your project folder, then start your agent with the setup skill:

~~~sh
cd path/to/your-project
claude "/af-setup"
~~~

| Agent | Run from your project folder |
|---|---|
| Claude Code | `claude "/af-setup"` |
| Codex | `codex "Use the af-setup skill"` |
| Cursor | `agent "Use the af-setup skill"` |

Setup reads your repository, asks a few questions, and shows every file it would write. Nothing is written until you approve. See [set up your project](setup.md).

Then describe your first change with `af-specify`, confirm the plan, and run `af-implement`. [Your first task](first-task.md) walks through it.

If your agent is already open, type `/af-setup` in Claude Code, or ask Codex or Cursor to use the `af-setup` skill. Its full name, `af-project-setup`, also works.

## If something goes wrong

| Message | What to do |
|---|---|
| *Python 3.11 or newer is required* | Install Python from [python.org](https://www.python.org/downloads/), open a new terminal, and run the install command again. |
| *Git is required* | Install Git from [git-scm.com](https://git-scm.com/downloads), open a new terminal, and run the install command again. |
| `agentflow: command not found` (Mac) | Run the *export PATH* line the installer printed, then open a new Terminal window. |
| *agentflow is not recognized* (Windows) | Open a new PowerShell window. The installer added the command to your PATH, but windows that were already open don't see it. |
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
The project gets its own copy at `.agentflow/bin/agentflow`, ignored by Git.

</details>
<details class="more" markdown>
<summary>Choose agents, or pin a version</summary>

~~~sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh -s -- --agents claude codex
curl -fsSL https://agentic.markoarsov.com/install.sh | AGENTFLOW_REF=v0.1.0 sh
~~~
On Windows, pass options the same way as the project install above, and pin with `$env:AGENTFLOW_REF = "v0.1.0"` before running the installer.

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
claude plugin install agentflow@agentflow
~~~
The plugin contains the same skills and runtime; its skills are named `agentflow:project-setup` and so on.
Use either the plugin or the installer for Claude Code, not both, to avoid duplicate skills.

</details>

## Before you run it

The scripts are short and readable: [install.sh](https://github.com/MarkoArsov/agent-workflow/blob/main/install.sh) and [install.ps1](https://github.com/MarkoArsov/agent-workflow/blob/main/install.ps1). They reject unsafe archive paths and verify the staged payload before switching versions; they do not verify a publisher signature.
Agent Flow was previously named Scorebook. The GitHub repository still uses its original name, agent-workflow.

To update or remove it later, see [update and remove](lifecycle.md).
