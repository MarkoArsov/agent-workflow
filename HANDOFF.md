# Local release handoff

Version 0.1.0 is implemented locally under the MIT license. Publication is a separate action.

## Delivered

- Global and self-contained project installers, ownership receipts, version pins, preserved overrides, rollback, and uninstall.
- Setup for one repository or a parent folder, read-only detection, complete proposals, explicit apply, and repeatable customization.
- 37 generic skills with Claude Code, Codex, and Cursor adapters; a validated native Claude plugin and marketplace.
- A resumable runner with fresh stages, exact-session input, fallback routes, independent checks, frozen tests, scope/index guards, environment leases, and guarded delivery.
- GitHub integration plus project connector declarations/command transports, configurable rules, and custom stages.
- A responsive MkDocs site, generated references, local search, strict link checks, CI, and a GitHub Pages workflow.

## Observed verification

- macOS / Python 3.14: all 50 automated tests passed using isolated homes, temporary repositories, provider doubles, and local bare remotes.
- Linux / Python 3.11: the same 50 tests passed in a disposable container with network access disabled.
- All 37 skills passed structural validation.
- Installed Codex, Claude, and Cursor command interfaces were checked. Claude strict manifest validation, local marketplace add, native install, inventory, update, and uninstall passed in a disposable configuration; inventory listed 37 skills.
- The real fixture application served an HTTP request from its companion test repository.
- Strict documentation build passed; 985 internal links/assets passed. Desktop/mobile layouts, navigation, and search were inspected in a browser.
- The release archive is reproducible; its allowlisted file manifest detects tampering.
- Source, generated site, existing Git history, and the 117-file extracted release payload passed the public-content scan with an external private denylist and zero findings. The scan includes names, content, and symlink targets.

Provider doubles are not live model generation. Account-authenticated runs, native Codex/Cursor invocation, hosted CI, Pages deployment, and published bootstrap installation remain release smoke checks. Native Windows is unsupported; use WSL. Restricted behavior depends on the selected provider controls; trusted execution is not an operating-system sandbox.

The implementation uses one provider command/event module and an installer-owned Python layout instead of separate provider files or a pip distribution. Documentation uses the built-in MkDocs theme with local CSS. These keep dependencies small without changing the agreed behavior.

Private source workspaces and real agent configuration were left unchanged. Public repository URLs use the approved public handle; normal Git author metadata uses the configured personal identity.

Local implementation commits: `9960904` (approved plan), `342d5c0` (runtime/installers), `c992901` (recovery/lifecycle verification), and `121fe1a` (documentation/Pages). The final handoff is recorded in a following local commit.

## Review locally

Run these commands from the repository root:

~~~sh
git status --short
git log --oneline --decorate
python3 -m unittest discover -s tests -v
python3 scripts/check_public_content.py --history
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python -m mkdocs build --strict
python3 scripts/check_links.py site
.venv/bin/python -m mkdocs serve
~~~

Optional installed-host checks: `python3 scripts/host_smoke.py`.
For a private provenance audit, add `--deny-file /path/to/private-denylist.txt` to the content scan; keep that file outside the repository.

## Publish when ready

These commands have not been executed. First verify the personal identity and account:

~~~sh
git config --show-origin user.name
git config --show-origin user.email
ssh -T git@github-personal
gh auth status
gh api user --jq .login
~~~

Confirm that GitHub reports `MarkoArsov`. GitHub's successful SSH greeting normally exits with code 1 because it provides no shell.
If the CLI is using another account, select the personal account before continuing.

Create the repository without a generated README or license, then publish the existing local history:

~~~sh
gh repo create MarkoArsov/agent-workflow --public --description "Customizable coding-agent workflows with verified execution."
git remote add origin git@github-personal:MarkoArsov/agent-workflow.git
git push -u origin main
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
~~~

In repository **Settings → Pages → Build and deployment**, select **GitHub Actions**.
Then run and inspect the workflows:

~~~sh
gh workflow run pages.yml --ref main --repo MarkoArsov/agent-workflow
gh run list --repo MarkoArsov/agent-workflow
~~~

Check [the documentation site](https://MarkoArsov.github.io/agent-workflow/), navigation, search, and assets under its project subpath. Review the Verify workflow results before announcing the release.

Build an optional downloadable payload:

~~~sh
python3 scripts/build_release.py
gh release create v0.1.0 .dist/stageway-0.1.0.tar.gz .dist/stageway-0.1.0.tar.gz.sha256 --repo MarkoArsov/agent-workflow --verify-tag --title "v0.1.0" --notes "Initial public release. See README and documentation for installation and support."
~~~

Finally, check the pinned bootstrap from a disposable home/project using both global and project install modes, then run the [real-host smoke procedure](docs/coverage.md#real-host-smoke-procedure) with an available model for each intended host.

~~~sh
curl -fsSL https://raw.githubusercontent.com/MarkoArsov/agent-workflow/v0.1.0/install.sh | sh -s -- --global
curl -fsSL https://raw.githubusercontent.com/MarkoArsov/agent-workflow/v0.1.0/install.sh | sh -s -- --project .
~~~

For a custom domain later, configure it and DNS in Pages, update `site_url` in `mkdocs.yml`, rebuild, and verify HTTPS and links. See [publication guidance](docs/publish.md).
