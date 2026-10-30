---
title: Commands and permissions
description: Configure commands, permissions, and provider routes for checked work.
question: How are commands, permissions, and model routes configured?
---

# Commands and permissions

!!! summary "In one minute"
    - Commands are argument arrays with a repository-relative working directory and a timeout; no shell is inserted.
    - Trusted mode uses provider permission-bypass flags. Restricted mode uses each provider's own controls.
    - Trusted mode is not operating-system containment.
    - Routes name a provider and model per stage, with an ordered list of fallbacks.

Commands use argument arrays, a repository-relative working directory, and a bounded timeout.
No shell is inserted automatically.

~~~json
{
  "argv": ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
  "cwd": ".",
  "timeout_seconds": 300
}
~~~

If a command deliberately invokes a shell, set `shell: true`.
Keep credentials in the host or named `env_refs`, never literal environment values in tracked configuration.

## Permission modes

| Provider | Trusted | Restricted |
|---|---|---|
| Codex | --dangerously-bypass-approvals-and-sandbox | workspace-write with unattended approval refusal |
| Claude | --dangerously-skip-permissions | dontAsk with a narrow allowed_tools list |
| Cursor | --force, --sandbox disabled, --trust | --sandbox enabled, --trust |

The orchestrator checks installed flags before execution. Unsupported controls stop preflight.
Restricted Claude preserves `execution.provider_settings.claude.allowed_tools`.
Otherwise plovi derives Read, Edit, Write, Glob, Grep, narrow Git status/diff rules
and the selected check argv. Unsafe command encodings stop preflight and ask for
an explicit allowlist. It never derives a broad Bash wildcard.

Detached and non-TTY runs default to restricted. An explicit
`execution.unattended_permission_mode = "trusted"` in [policy](policy.md), or
`run --trusted`, opts in to trusted unattended work. Interactive runs keep the
profile mode. Preflight and run state show the mode and source; detach and resume
retain the decision. Runner-owned checks and selected delivery actions keep their
existing contracts; provider tool restrictions do not restrict those commands.

These providers offer different controls; restricted mode is not an identical cross-provider sandbox.
Trusted mode relies on configured access and post-stage outcome checks. It is not operating-system containment.

## Routes

A route names the provider, model, and optional reasoning setting. A stage can have an ordered fallback list.

~~~json
{
  "pipeline": {
    "routes": {
      "default": [
        {"provider": "codex", "model": "YOUR_CODEX_MODEL", "reasoning": "high"}
      ]
    }
  }
}
~~~

Setup records your chosen models. Preflight checks command compatibility; model/account availability is established when the provider receives the request.
Cursor effort belongs in its supported model expression.

[Model and cost choices](models.md) · [Evidence formats](verification.md)

<!-- checkpoints: EXE-1, EXE-4, ORG-3 -->

!!! note "What changes for your workflow"
    Unattended runs use restricted controls by default. Review policy or pass
    `--trusted` for a deliberate exception. Extend Claude's explicit allowlist
    when a configured check cannot be encoded safely.
