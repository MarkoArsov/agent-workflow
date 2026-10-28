# Reliable GitHub Actions verification

Status: proposed; implementation requires approval.
Lane: in-session implementation with behavioral regression tests and final review.

## Request

Fix and improve GitHub Actions CI, which appears unreliable and fails when it should pass.

## Evidence

- Verify run 40723112440 at commit c10a0cb: docs and Windows installation succeeded. All six core matrix jobs failed only in check_public_content.py --history, on `17fc906e:message: email`. The failing email is a public automated co-author address in an existing design commit, not a file introduced by the setup PR.
- Main run 40721639002 reports the same finding on every OS/Python pair. Windows core jobs in run 40723112440 took about 17–18 minutes; the history step enumerates every file in every commit through separate Git processes.
- Run 40730566027 on main has the same initial Linux failures; other matrix jobs were still running during research. Do not claim its final outcome yet.
- Verify currently triggers on every push and pull request. The two runs 40723112440 and 40723108417 cover the same feature revision.
- Older run 38745429925 failed with Python 3.11 import-time f-string syntax errors. Those are genuine failures fixed by f4afa77, not evidence of flaky tests.
- Existing examples: .github/workflows/verify.yml, .github/workflows/pages.yml, scripts/check_public_content.py, tests/helpers.py, tests/test_release.py. Preserve isolated fixture homes and the six supported OS/Python test combinations.
- GitHub documents that PR runs check a synthetic merge commit by default. Keep that behavior and avoid downloading its SHA through the public archive endpoint for the required installer check.

Sources:
- https://github.com/MarkoArsov/agent-workflow/actions/runs/40723112440
- https://github.com/MarkoArsov/agent-workflow/actions/runs/40721639002
- https://github.com/MarkoArsov/agent-workflow/actions/runs/38745429925
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

## Scope and behavior

One writable repository: agent-workflow, current checkout as configured. Before implementation, refresh origin/main and prepare a new codex/ci-reliability branch from the latest approved base without altering unrelated local work. The setup PR branch is not the delivery branch for this separate change.

Writable implementation paths: .github/workflows/verify.yml, scripts/check_public_content.py, tests/test_public_content.py, tests/test_ci_workflow.py, and narrowly relevant CI troubleshooting documentation under docs/. Keep all other runtime, installation, and design behavior unchanged.

1. Correct the content scanner's treatment of the reviewed public automated attribution. Exempt only the exact reviewed address in a well-formed Co-Authored-By trailer in a commit message. Ordinary emails in file contents, other personal emails in trailers/messages, credentials, private paths, and supplied private-denylist matches must still fail. Do not skip commit messages, suppress errors, rewrite history, or introduce a broad email-domain exemption. Do not add attribution trailers to new commits.
2. Keep full reachable-history scanning while avoiding repeated Git subprocesses and rescanning unchanged content. Batch-read unique blobs; preserve path-sensitive checks, all reachable commit messages, deletion/history findings, symlink targets, and non-UTF-8 handling. Retain actionable, redacted diagnostics. Never emit matched secret values. Compare findings to a fixture reference traversal; assert deduplicated work with operation counts rather than fragile wall-clock thresholds.
3. Run generated-document and full-history public-content checks once in a dedicated Ubuntu job. Keep unittest coverage on Ubuntu, macOS, and Windows for Python 3.11 and 3.14. Matrix checkouts need not fetch full history; the audit checkout must. Use clear step/job names and explicit job timeouts.
4. Verify PRs and pushes to main, plus allow workflow_dispatch for a branch before it has a PR. This intentionally replaces duplicate feature-push/PR runs. Add workflow-specific per-ref/PR concurrency to cancel superseded verification runs without affecting the Pages deployment workflow. Keep read-only default permissions and credential-free checkout. Check repository-required job names before renaming; do not edit branch-protection settings.
5. Make the required Windows installation smoke check use the checked-out source, covering Windows PowerShell 5.1 installation and PowerShell 7 reinstall in isolated temporary home/configuration directories. Verify the installed command, discovery file, and reinstall behavior. Avoid requiring a GitHub archive/network download for correctness of local installation. Keep existing isolated installer/bootstrap tests; clearly document that remote bootstrap availability is separate release smoke evidence, not proven by this check.
6. On failures, retain concise test/audit logs as artifacts and useful job summaries without credentials or real user configuration. Do not add automatic retries for test assertions or audits; failures must remain blocking.

## Implementation and checks

1. Add focused behavioral tests first. Demonstrate assertion failures for the public-attribution exception and repeated-history work before changing the scanner. Use only temporary Git repositories and fixture identities; no real home/configuration mutation or external credentials. Workflow contract checks should cover meaningful trigger, matrix, local-install, isolation, and gating behavior, not snapshots of formatting.
2. Implement scanner and workflow changes, keeping Python 3.11+ and the standard library for runtime and test helpers. No new runtime dependency or required service.
3. Review the diff against these requirements, then run:
   - `python3 -m unittest discover -s tests -p test_public_content.py -v` (behavioral red/green and negative cases).
   - `python3 -m unittest discover -s tests -p test_ci_workflow.py -v` (workflow contracts).
   - `python3 -m unittest discover -s tests -v` (entire isolated suite; local test-server access required).
   - `python3 scripts/generate_docs.py --check`.
   - `python3 -m mkdocs build --strict` using the existing documentation environment.
   - `python3 scripts/check_links.py site`.
   - `python3 scripts/check_public_content.py --history` and `python3 scripts/check_public_content.py site`.
   - `git diff --check`.
   Use targeted checks with 120-second limits, full suite with 600 seconds, history audit with 300 seconds, docs/link checks with 120 seconds. Adjust only on observed evidence and report changes.
4. Acceptance fixtures: accepted reviewed public trailer; rejected arbitrary/private trailer and same public address in an ordinary file; credentials and private paths still rejected; denylist overrides attribution allowance; deleted historical finding survives; repeated blobs scanned once; path/symlink/non-UTF-8 cases remain covered; changing a file later does not hide its earlier finding. Generated artifacts remain excluded as before where appropriate.
5. Commit the verified implementation locally, with a clean final tree. Hosted Linux/macOS/Windows results must be reported separately from local checks. No hosted green claim until a run for the implementation revision actually passes.

## Delivery and deferred work

Execution permission mode: project trusted setting, within the approved scope. Agents: Codex and Cursor only. No Claude route or delegation. The offline evaluator ran once; model-selection.json records no available configured route/catalogue. In-session work can continue with the active Codex model after approval; detached orchestration requires resolved model routes first.

This plan authorizes local changes and commits only. Pushing, opening another PR, triggering remote workflows, changing protection rules, issue/board updates, deployment, and publication require a separate explicit request. Existing unrelated remote actions are not covered by earlier setup delivery authorization.

Defer Pages redesign, hosted runner replacement, broad action/version upgrades, removing OS coverage, release/bootstrap redesign, blanket retry policies, and history rewriting. No evidence currently justifies them. Remote download smoke tests may be proposed separately if needed; do not silently remove claims from the support matrix.

Approval requested: Approve this plan and start implementation?
