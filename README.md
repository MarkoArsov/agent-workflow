<p align="center">
  <img src="docs/assets/brand/mark.svg" width="72" height="72" alt="plovi logo">
</p>

<h1 align="center">plovi</h1>

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

You confirm one plan. plovi runs it in stages, and each stage has to show its work:

| Stage | What happens | What the orchestrator keeps |
|---|---|---|
| **Specify** | Research first, then one complete plan where every outcome maps to a named check. | Plan files and a validated `pipeline.json` |
| **Tests** *(optional)* | Written before the code. They must fail on an assertion, then they're frozen. | Red proof and test-file hashes |
| **Implement** | Build, run the named checks, fix. The orchestrator then runs the checks itself. | Parsed results tied to the current diff |
| **Review** *(optional)* | A fresh session that sees the requirements and diff, not the author's reasoning. | Findings, and checks re-run after fixes |
| **Deliver** *(optional)* | Commit, push, and draft PR. Never to a base branch, never a force push. | A delivery record per repository |

Small change? Run `specify`, then `implement`, in one session.

## Install

You need Python 3.11+, Git, and Claude Code, Codex, or Cursor.

**Mac or Linux:** open Terminal and run

```sh
curl -fsSL https://agentic.markoarsov.com/install.sh | sh
```

**Windows:** open PowerShell and run

```powershell
irm https://agentic.markoarsov.com/install.ps1 | iex
```

Then open a new terminal window and check it with `plovi --version`. The installer finds your agents and prints the command to start setup. [Full install guide](https://agentic.markoarsov.com/install/)

## Quick start

1. From your project folder, run `claude "/plovi-setup"` (or ask Codex or Cursor to use the **`plovi-setup`** skill). Approve the setup it proposes.
2. Run **`plovi-specify`** with what you want built, and confirm the plan.
3. Run **`plovi-implement`**.

That's it. For bigger changes, `plovi-implement-pipeline` runs the full staged pipeline instead. See [your first task](https://agentic.markoarsov.com/first-task/).

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

For a live development checkout, use `python3 install.py --global --link` and
`python3 install.py --global --sync` after adding or renaming skills. See the
[linked installation guide](docs/install.md#follow-a-development-checkout).

### What changes for your workflow

Reinstall to use `plovi` and `/plovi-<skill>`. The `agentflow` command and
`/af-<skill>` aliases keep working until 1.0 and print a short deprecation note.
Finish or cancel running tasks before upgrading. On the first normal run of the
new runtime, each project's `.agentflow/` directory moves to `.plovi/`, with one
notice. If both directories exist, plovi stops and preserves both for you to
resolve. Setup and installation previews report the move without performing it.
See [upgrade details](https://agentic.markoarsov.com/install/#upgrade-to-plovi).
