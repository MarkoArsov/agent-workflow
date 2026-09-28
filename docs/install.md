---
title: Install
description: Install Agent Flow with one command, then set up your project.
footer: docs
footer_order: 1
question: How do I install Agent Flow?
---

# Install

!!! summary "In one minute"
    - Run one command. It installs the `agentflow` command and the `af-*` skills for the agent CLIs it finds.
    - Then open a project in your agent and run `af-project-setup`.
    - You need Python 3.11+, Git, and Claude Code, Codex, or Cursor. macOS and Linux; use WSL on Windows.

## 1. Install

~~~sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh
~~~

The installer checks for Python and Git, downloads the latest release (or `main` until the first release is tagged), and installs for your user account.
It adds skills for each agent CLI it finds on your machine: Claude Code, Codex, or Cursor.
When it finishes, it prints where the `agentflow` command went and what to do next. If `~/.local/bin` isn't on your `PATH`, it prints the line to add.

## 2. Set up your project

Open your project in your agent and run the setup skill:

| Agent | Type |
|---|---|
| Claude Code | `/af-project-setup` |
| Codex, Cursor | Ask it to use the `af-project-setup` skill |

Setup reads your repository, asks a few questions, and shows every file it would write. Nothing is written until you approve. See [set up your project](setup.md).

## 3. Start a task

Run `af-specify` with what you want built, confirm the plan, then run `af-implement`. [Your first task](first-task.md) walks through it.

## Other ways to install

<details class="more" markdown>
<summary>Into one project instead of your user account</summary>

~~~sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh -s -- --project .
~~~
The project gets its own copy at `.agentflow/bin/agentflow`, ignored by Git.

</details>
<details class="more" markdown>
<summary>Choose agents, or pin a version</summary>

~~~sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh -s -- --agents claude codex
curl -fsSL https://agentic.markoarsov.com/install.sh | AGENTFLOW_REF=v0.1.0 sh
~~~

</details>
<details class="more" markdown>
<summary>From a clone, without the script</summary>

~~~sh
git clone https://github.com/MarkoArsov/agent-workflow.git
python3 agent-workflow/install.py
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

The script is short and readable: [install.sh](https://github.com/MarkoArsov/agent-workflow/blob/main/install.sh). It rejects unsafe archive paths and verifies the staged payload before switching versions; it does not verify a publisher signature.
Agent Flow was previously named Scorebook. The GitHub repository still uses its original name, agent-workflow.

To update or remove it later, see [update and remove](lifecycle.md).
