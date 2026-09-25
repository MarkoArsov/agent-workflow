---
title: Contribute and develop
description: Contribute to Scorebook, run its checks, and change a public contract safely.
question: How do I contribute to Scorebook?
---

# Contribute and develop

!!! summary "In one minute"
    - Scorebook is MIT-licensed and developed in the open. Contributions are welcome.
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
python3 -m unittest discover -s tests -v
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
