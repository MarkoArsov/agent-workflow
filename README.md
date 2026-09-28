<p align="center">
  <img src="docs/assets/brand/mark.svg" width="72" height="72" alt="Agent Flow logo">
</p>

<h1 align="center">Agent Flow</h1>

<p align="center">
  <strong>Agents write the code. The orchestrator makes them prove it.</strong><br>
  An open-source workflow for Claude Code, Codex, and Cursor that checks every stage.
</p>

<p align="center">
  <a href="https://agentic.markoarsov.com/"><strong>Website and docs</strong></a> ·
  <a href="https://agentic.markoarsov.com/first-task/">Your first task</a> ·
  <a href="https://agentic.markoarsov.com/scorecard/">Checkpoint scorecard</a> ·
  <a href="LICENSE">MIT license</a>
</p>

---

## What it does

You confirm one plan. Agent Flow runs it in stages, and each stage has to show its work:

| Stage | What happens | What the orchestrator keeps |
|---|---|---|
| **Specify** | Research first, then one complete plan where every outcome maps to a named check. | Plan files and a validated `pipeline.json` |
| **Tests** *(optional)* | Written before the code. They must fail on an assertion, then they're frozen. | Red proof and test-file hashes |
| **Implement** | Build, run the named checks, fix. The orchestrator then runs the checks itself. | Parsed results tied to the current diff |
| **Review** *(optional)* | A fresh session that sees the requirements and diff, not the author's reasoning. | Findings, and checks re-run after fixes |
| **Deliver** *(optional)* | Commit, push, and draft PR. Never to a base branch, never a force push. | A delivery record per repository |

Small change? Run `specify`, then `implement`, in one session.

## Install

```sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh
```

Needs Python 3.11+, Git, and Claude Code, Codex, or Cursor. macOS and Linux; WSL on Windows. The installer finds your agent CLIs and prints the next step. [Other ways to install](https://agentic.markoarsov.com/install/)

## Quick start

1. Open your project in your agent and run **`af-project-setup`** (in Claude Code: `/af-project-setup`). Approve the setup it proposes.
2. Run **`af-specify`** with what you want built, and confirm the plan.
3. Run **`af-implement`**.

That's it. For bigger changes, `af-implement-pipeline` runs the full staged pipeline instead. See [your first task](https://agentic.markoarsov.com/first-task/).

## Why trust it

- **Evidence, not claims.** The orchestrator runs every check itself and records what it saw.
- **Stops only for what matters.** Scope, secrets, frozen tests, failed checks, and delivery guards block. Review notes don't.
- **Honest about limits.** A public [36-point scorecard](https://agentic.markoarsov.com/scorecard/) shows what's covered and what isn't.
- **Yours to change.** Override skills, add rules, stages, and connectors per project, without forking.
- **Open and local.** MIT license, standard-library Python, no account, no server, no telemetry.

## Contributing

```sh
python3 -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for docs builds and checks, and [Contribute and develop](https://agentic.markoarsov.com/development/) for the full guide.
