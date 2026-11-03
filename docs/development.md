---
title: Contribute and develop
description: Contribute to plovi, run its checks, and change a public contract safely.
question: How do I contribute to plovi?
---

# Contribute and develop

!!! summary "In one minute"
    - plovi is MIT-licensed and developed in the open. Contributions are welcome.
    - Runtime code is Python 3.11+ with the standard library only, and no new dependencies without a concrete need.
    - A good change comes with tests for its behavior and failure modes, and keeps schemas, validation, skills, and docs aligned.
    - Run the same checks CI runs before you open a pull request.

## Contributing

What makes a good change:

- It solves a concrete, named problem, in the one place that owns that behavior.
- It keeps the package generic. Project-specific behavior belongs in a project's profile and extensions, not in bundled defaults.
- It never copies private source material, credentials, personal machine paths, or historical task content into examples.

Add tests for behavior and meaningful failure modes rather than mirroring implementation details.
Tests create temporary homes, repositories, provider doubles, and local remotes; they never touch your real agent configuration or accounts.

Keep commits focused and imperative, without attribution trailers.
A pull request explains the concrete problem, the resulting behavior, and the validation you actually observed.

## Run the checks

Python 3.11+ runs the installer, runtime, and tests with the standard library.
The checkout uses an installer-owned layout rather than a pip distribution.

~~~sh
python3 scripts/run_tests.py --jobs auto
python3 scripts/generate_docs.py --check
python3 scripts/check_public_content.py --history
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python -m mkdocs build --strict
.venv/bin/python scripts/check_links.py site
.venv/bin/python -m mkdocs serve
~~~

The E2E fixture needs permission to listen on localhost.
Tests must use their isolated HOME and provider configuration; never test installation against your real settings.

### Run tests quickly

`scripts/run_tests.py` runs the suite in worker processes. Plain
`python3 -m unittest discover -s tests -v` still works and runs everything serially.

| Command | What it runs |
|---|---|
| `--jobs auto` | Every test, in up to 8 workers (one per CPU). `--jobs N` picks the count. |
| `--changed` | Tests that import a changed `runtime/plovi` module or were changed themselves, plus the smoke tier. Compares with `origin/main`, else `main`; `--base REF` picks another. |
| `--tier smoke` | The fast modules listed in `tests/tiers.json`. |
| `--per-test-timeout 30` | Fails a test that runs longer than 30 seconds. The default is 120, or `PLOVI_TEST_TIMEOUT`. |
| `--shard 1 --shards 3` | One of three batches of similar estimated time, as a CI job runs them. Combines with `--jobs`. |
| `--list` | The selected test IDs, without running them. |

While you fix something, run `--changed`. Before a pull request, run `--jobs auto`.
When only documentation or task plans changed, `--changed` selects no tests and
says to run the docs checks. A workflow change selects the CI workflow tests, and
any other file selects the tests that name it. A change to `tests/helpers.py`, a
fixture, or a file no test names selects every test.

Batches and workers are balanced by estimated time per test, longest first.
Estimates come from `tests/timings.json`, which holds each test's time on Linux,
macOS and Windows in CI. Locally, the timings a run records in
`.plovi/local/test-timings.json`, which Git ignores, take precedence for workers.
Batches use only the committed file, so every CI job computes the same split.
Each worker prints its output when it finishes. All failures follow at the end,
with the ten slowest tests.

When a CI batch drifts well past five minutes, refresh the weights from a recent run:

```sh
gh run download RUN_ID --pattern 'tests-*' --dir runs
python3 scripts/update_test_weights.py runs/*/test-timings.json
```

A test that exceeds its timeout prints the stack of every thread and fails. Its
worker stops, and the tests it had not reached are reported as not run. The other
workers carry on. A worker that exits without results fails the run and names
its modules.

CI runs a smoke job first: it compiles the sources, runs the smoke tier and checks
generated documentation. The full matrix starts only when smoke passes. Pull
requests run Ubuntu with Python 3.11 and 3.14 in two batches each, macOS with 3.14
in three, and Windows with 3.14 in eight. Each batch runs about five minutes of
tests. A nightly workflow also runs macOS and Windows with 3.11.

Test commands that stand in for `gh`, providers or Docker are Python scripts. Install
them with `install_script` from `tests/helpers.py`: on Windows it builds an `.exe`, because
a `.cmd` shim passes its arguments through cmd.exe, which splits them at `&` and newlines.
CI keeps each job's log, worker results and per-test timings for seven days,
including successful runs.

### Scenario tests: how to own a step

`tests/scenario` holds the [target scenario](generated/scenario.md): one test per step in
`tests/scenario/steps.py`, each decorated `@owned_by(...)` with the issues that own it.
`tests/scenario/owners.json` marks each owner `done` or `pending`. A step runs only when
all its owners are done; until then it is skipped with "owned by #N (pending)".

To own a step in your pull request:

1. Replace the step's `self.fail("not implemented")` stub with a real test. Use the
   fixture projects (`self.project("hobby")` or `self.project("product")`), the provider
   double (`self.provider([...])`) and `self.install_github_fake(state)` for GitHub.
2. Set your issue to `done` in `owners.json` once all your steps have tests.
3. Run `python3 scripts/generate_docs.py` so `docs/generated/scenario.md` shows the new status.

Flipping an owner without a test fails, and `test_traceability` fails when a step has no
owner, no test method, or an owner missing from `owners.json`. Keep the GitHub fake dumb:
add a handler for each new `gh` call your code makes, and nothing a test didn't script.
An unmapped call exits 99 and prints its arguments. `python3 scripts/run_tests.py
--scenario-results PATH` writes each step's result; CI keeps it for the
[stability gate](stability-gate.md).

The optional local host check, `python3 scripts/host_smoke.py`, validates installed command interfaces and exercises Claude plugin lifecycle in a temporary configuration. It does not generate model responses or publish anything.

## One source of truth

Canonical skills live under skills/. Schemas describe the public formats.
The documentation hook regenerates references from only those allowlisted package sources.
It does not read local profiles, plans, evidence, logs, or private material.

Use `python3 scripts/generate_docs.py --check` to detect stale generated references and invalid checkpoint data.
The checkpoint scorecard is generated from `docs-data/checkpoints.json`; the build fails if a checkpoint cites a file that doesn't exist, uses an unknown status, or if there aren't exactly 36.
Diagrams keep their Mermaid source next to a hand-built HTML rendering in `docs-data/diagrams/`, so the site loads no diagram library.
Build and inspect desktop/mobile layouts before changing navigation or CSS.

## Build an installable archive

~~~sh
python3 scripts/build_release.py
~~~

This writes a deterministic archive and SHA-256 sidecar under `.dist/`.
The allowlisted payload excludes local configuration, tests, documentation builds, and Git metadata.
A per-file checksum manifest detects edited or incomplete packaged contents during installation.
Checksums detect corruption; they do not authenticate a publisher independently.

## Change a contract carefully

Keep examples, runtime validation, schemas, tests, and documentation aligned.
Test user-visible failure modes and preservation behavior.
Do not add dependencies or broad abstractions without a concrete need.

Before release, scan filenames, content, symlink targets, generated site, payload, and reachable history.
An optional external denylist can check private provenance without committing forbidden terms.

## Where help is most useful

The [open frontier](scorecard.md#the-open-frontier) lists the next engineering problems: operating-system isolation, egress control, scoped credentials, evidence in the pull request, and telemetry.
Anything marked partial on the [checkpoint scorecard](scorecard.md) is a good place to start.

<!-- checkpoints: ORG-5, CTX-4 -->

## See also

[Open source](open-source.md) · [Code map](code-map.md) · [Publish a release](publish.md) · [How it's tested](coverage.md)

## Documentation design assets

`design/tokens.json` is the source for color, type, spacing and size. The docs use
the supplied Geist fonts, sailboat SVGs, and components. After editing the design,
run `python3 scripts/sync_docs_design.py`; use `--check` to detect stale copies.
The generated Mermaid theme files in `docs-data/diagrams/` use the same colors.
The hand-rendered HTML diagrams inherit the active theme through CSS variables.

Rebuild the committed PNG derivatives with `python3 scripts/generate_brand.py`.
This development command needs Node, Playwright, and an existing Chromium. It
performs no downloads. Use `--node`, `--node-modules`, and `--chromium` to select
existing tools if needed; they are not runtime dependencies. Both PNGs render
from the supplied SVGs with the supplied Geist font in an isolated browser profile.
