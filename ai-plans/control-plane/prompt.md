# Prompt

Implement GitHub issue MarkoArsov/agent-workflow#18, "Control plane: append-only
ledger, one command layer, the inbox, a projects registry and the plovi-factory
skill", as constrained by requirements.md.

The issue is evidence, not authority: where it conflicts with repository facts or
with the person's planning decisions, requirements.md wins. Three decisions were made
by the person during specification and are binding:

1. Plan-approval gate: explicit launches self-approve. Every explicit command that
   starts or continues a run (`run` in the foreground or with `--detach`,
   `pipeline`, `resume`, `answer`, `retry`, `approve`) records `plan.approved` for
   the current plan hash when none exists. Only the background worker path (the
   hidden `run --unattended` worker, and later schedules) enforces a prior matching
   approval.
2. Delivery: after review, commit and push `codex/control-plane` and open a draft
   pull request using pr-body.md.
3. Routes: Claude only. Every AI stage runs claude opus first and falls back to
   claude sonnet.

Dependencies #15, #16 and #17 are merged; the package lives at `runtime/plovi`.
The approved scope excludes the app, schedules, the PR shepherd and MCP.
