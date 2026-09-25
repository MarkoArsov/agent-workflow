---
title: Open source
description: What is open, how to audit it, and how to change or contribute to it.
question: What exactly is open, and how can I use, audit, and extend it?
---

# Open source

!!! summary "In one minute"
    - Scorebook is MIT-licensed. Everything that runs is in the public repository.
    - It runs locally with your own agent CLIs. There is no Scorebook account, server, or telemetry.
    - Change it per project without forking, or fork the whole thing.
    - Its own [checkpoint scorecard](scorecard.md) is public, gaps included. Contributions are welcome.

## What's in the repository

| Folder | What it is |
|---|---|
| [`runtime/scorebook/`](https://github.com/MarkoArsov/agent-workflow/tree/main/runtime/scorebook) | The runner, check parsers, path and rule guards, run journal, provider commands, environments, and delivery. See the [code map](code-map.md). |
| [`skills/`](https://github.com/MarkoArsov/agent-workflow/tree/main/skills) | Every bundled skill. The [skill reference](generated/skills.md) is generated from these files. |
| [`schemas/`](https://github.com/MarkoArsov/agent-workflow/tree/main/schemas) | The public formats for projects, plans, rules, stages, and connectors. See the [schema reference](generated/schemas.md). |
| [`references/`](https://github.com/MarkoArsov/agent-workflow/tree/main/references) | The plan contract, project profile guidance, and environment lifecycle guidance that stages load on demand. |
| [`templates/`](https://github.com/MarkoArsov/agent-workflow/tree/main/templates) | Host discovery adapters, the launcher, and this site's theme. |
| [`install.py`](https://github.com/MarkoArsov/agent-workflow/blob/main/install.py), [`install.sh`](https://github.com/MarkoArsov/agent-workflow/blob/main/install.sh) | The offline installer and the pinned-release bootstrap. |
| [`tests/`](https://github.com/MarkoArsov/agent-workflow/tree/main/tests) | The automated suite, with temporary repositories and labeled provider doubles. See [how it's tested](coverage.md). |
| [`docs/`](https://github.com/MarkoArsov/agent-workflow/tree/main/docs) | This site. |

## Why it matters for a verification tool

A verification layer you can't inspect is just another claim to trust.
With Scorebook you can read exactly what "passed" means:

- the [parsers](verification.md#green-evidence) that decide whether a unittest, pytest, .NET, Jest, TAP, or generic check succeeded;
- the rule that rejects import and compile errors as red evidence;
- the path guard that fails a stage writing outside its declared paths;
- the secret detector and your blocking rules;
- the delivery guards that refuse base branches and unrelated staged changes.

Nothing is judged by a service you can't see. The [code map](code-map.md) shows where each of these lives.

## Runs on your machine

- The runtime is standard-library Python with zero runtime dependencies.
- The runtime opens no network connections of its own. Network traffic goes through your agent CLIs, `git`, and `gh`. The optional bootstrap installer uses `curl` to download the pinned release archive.
- Credentials stay in your agent and GitHub logins, or in environment variables you name with `env_refs`. Command environments and connector settings reject literal values with secret-looking names.
- There is no Scorebook account, server, or telemetry. Run evidence stays in your project.
- This site has no analytics, remote fonts, or connection to your local workflow state.

## No lock-in

Three ways, from lightest to heaviest:

1. **Any harness, any model, per stage.** Claude Code, Codex, or Cursor, with the model you choose. See [cost and models](models.md).
2. **Project-owned overrides.** Copy a bundled skill, add your own skills, rules, connectors, and stages. Updates preserve them. See [skills and stages](customize.md).
3. **The MIT license.** If you want to take it somewhere else entirely, you can.

## Built in the open

- **Public CI.** On every push and pull request, GitHub Actions runs the test suite on Linux and macOS with Python 3.11 and 3.14, checks generated references, and scans the source and its history for private content. A separate job builds this site in strict mode, checks every internal link, and scans the built pages.
- **A public scorecard.** The [checkpoint scorecard](scorecard.md) states what the runner enforces, what is partial, what belongs to your organization, and what is still missing.
- **An open roadmap.** The [open frontier](scorecard.md#the-open-frontier) lists the next engineering problems. Those are the places contributions help most.

## Contribute

- Use Python 3.11+ and the standard library for runtime work. Install through `install.py`; this is not a pip distribution.
- Add tests for behavior and meaningful failure modes, not mirrors of the implementation.
- When you change a contract, keep schemas, validation, examples, skills, and documentation aligned.
- Keep commits focused and imperative, without attribution trailers.
- A pull request explains the concrete problem, the resulting behavior, and the validation you observed.

[Contribute and develop](development.md) has the full commands.
Good first areas are the [open frontier](scorecard.md#the-open-frontier) and anything marked partial on the scorecard.

## License

Scorebook is released under the [MIT license](https://github.com/MarkoArsov/agent-workflow/blob/main/LICENSE): use it, change it, and ship it, keeping the copyright and license notice.

<!-- checkpoints: ORG-5, CTX-1 -->

## See also

[Code map](code-map.md) · [Contribute and develop](development.md) · [Security boundary](security.md)
