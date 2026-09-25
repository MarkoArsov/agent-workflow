<p align="center">
  <img src="docs/assets/brand/mark.svg" width="72" height="72" alt="Scorebook logo">
</p>

<h1 align="center">Scorebook</h1>

<p align="center">
  <strong>Agents write the code. Scorebook makes them prove it.</strong><br>
  An open-source workflow for Claude Code, Codex, and Cursor that checks every stage.
</p>

<p align="center">
  <a href="https://MarkoArsov.github.io/agent-workflow/"><strong>Website and docs</strong></a> ·
  <a href="https://MarkoArsov.github.io/agent-workflow/first-task/">Your first task</a> ·
  <a href="https://MarkoArsov.github.io/agent-workflow/scorecard/">Checkpoint scorecard</a> ·
  <a href="LICENSE">MIT license</a>
</p>

---

## What it does

You confirm one plan. Scorebook runs it in stages, and each stage has to show its work:

| Stage | What happens | What the runner keeps |
|---|---|---|
| **Specify** | Research first, then one complete plan where every outcome maps to a named check. | Plan files and a validated `pipeline.json` |
| **Tests** *(optional)* | Written before the code. They must fail on an assertion, then they're frozen. | Red proof and test-file hashes |
| **Implement** | Build, run the named checks, fix. The runner then runs the checks itself. | Parsed results tied to the current diff |
| **Review** *(optional)* | A fresh session that sees the requirements and diff, not the author's reasoning. | Findings, and checks re-run after fixes |
| **Deliver** *(optional)* | Commit, push, and draft PR. Never to a base branch, never a force push. | A delivery record per repository |

Small change? Run `specify`, then `implement`, in one session.

## Install

Requires Python 3.11+, Git, and at least one signed-in agent CLI (Claude Code, Codex, or Cursor). The GitHub CLI is needed only for pull requests. macOS and Linux; use WSL on Windows. No Python dependencies.

```sh
git clone https://github.com/MarkoArsov/agent-workflow.git
cd agent-workflow
python3 install.py --global                    # for all projects
python3 install.py --project /path/to/project  # or for one project
```

A one-line `curl` installer and the native Claude plugin are available once a release is tagged. See [Install](https://MarkoArsov.github.io/agent-workflow/install/).

## Quick start

1. In your project, ask your agent to run **`sb-project-setup`** and approve the proposal it shows you.
2. Run **`sb-specify`** with your task and confirm the plan.
3. For a small change, run **`sb-implement`**. For the full pipeline:

```sh
scorebook run ai-plans/my-task/pipeline.json --detach
scorebook status my-task
```

In the native Claude plugin, the skills are named `scorebook:specify` and so on.

## Why trust it

- **Evidence, not claims.** The runner runs every check itself and records what it saw.
- **Stops only for what matters.** Scope, secrets, frozen tests, failed checks, and delivery guards block. Review notes don't.
- **Honest about limits.** A public [36-point scorecard](https://MarkoArsov.github.io/agent-workflow/scorecard/) shows what's covered and what isn't.
- **Yours to change.** Override skills, add rules, stages, and connectors per project, without forking.
- **Open and local.** MIT license, standard-library Python, no account, no server, no telemetry.

## Contributing

```sh
python3 -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for docs builds and checks, and [Contribute and develop](https://MarkoArsov.github.io/agent-workflow/development/) for the full guide.
