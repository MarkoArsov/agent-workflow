---
description: Build, test, and update the standalone agent-workflow package.
---

# Develop the workflow

Python 3.11+ runs the installer, runtime, and tests with the standard library.
The checkout uses an installer-owned layout rather than a pip distribution.

~~~sh
python3 -m unittest discover -s tests -v
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

Use `python3 scripts/generate_docs.py --check` to detect stale generated references.
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

[Publication procedure](publish.md) · [Coverage](coverage.md)
