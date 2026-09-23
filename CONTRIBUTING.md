# Contributing

Keep the public package generic and project configuration portable. Do not copy private source material, credentials, personal machine paths, or historical task content into examples.

Use Python 3.11+ and the standard library for runtime work. Install through install.py; this is not a pip distribution.

~~~sh
python3 -m unittest discover -s tests -v
python3 scripts/generate_docs.py --check
python3 scripts/check_public_content.py --history
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python -m mkdocs build --strict
.venv/bin/python scripts/check_links.py site
~~~

Tests create temporary homes, repositories, provider doubles, and local remotes.
The E2E fixture listens on localhost. Never use a real agent configuration or account just to test installation or publishing.

Update schemas, validation, examples, skills, and documentation together when changing a contract.
Add tests for behavior and meaningful failure modes rather than mirroring implementation details.
Review desktop and mobile layouts when changing the site.

Keep commits focused, imperative, and free of attribution trailers.
A pull request should explain the concrete problem, resulting behavior, and observed validation.

Publication and deployment are separate maintainer actions. See [the release procedure](docs/publish.md).
