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

## Select a Claude account

To keep a project's Claude usage on a specific personal login, create the ignored
project-local file `.plovi/local/claude-account.json` with `config_dir` set to the
absolute path of that Claude configuration directory and `email` set to the login
email. Create `.plovi/local/claude-account.required` alongside it to make a missing
account file stop the run. Keep both local; they do not belong in a repository.

Before managed stages, checks and environment services, plovi checks `claude auth
status` with that configuration and requires a matching first-party Claude login.
It passes the selected configuration to subprocesses. Credential or backend
overrides stop execution instead of silently choosing another account. Account
verification requires a signed-in Claude CLI; it does not change native logins.
This is an account-selection guard for managed processes, not a containment
boundary against a program deliberately changing its own environment.

A provider completion without a valid final report stops for inspection rather
than automatically repeating the attempt. Use the reported retry command only
after inspecting the retained output.

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

## Private provider selection

Optional `.plovi/local/provider-identities.json` stores host-local selectors and
verification policy. It is ignored and must never be exported with public profiles.
Each provider entry accepts `config_env` and `verification` (`allow-unverified` or
`required`). Supported selectors are `CODEX_HOME` for Codex and `CLAUDE_CONFIG_DIR`
for Claude; Cursor has no assumed configuration selector. Use absolute local paths.

Claude required verification uses the account guard above. For providers without
a supported account verifier, required verification stops preflight; selecting a
config directory alone is not proof of account identity. Preflight reports this
limitation explicitly. plovi does not switch global accounts or run paid health
probes. Model availability is checked by the provider on the actual request.

An opaque selector fingerprint is bound to the task. Changing selectors requires
reviewed rebind; changes during a managed run stop before its next subprocess.
Claude identity is checked again before managed stages, checks and services.
Public task evidence contains no expected email or private config directory.

## Factory and container execution

New unattended CLI runs use independent factory checkouts even when interactive
setup chose a shared checkout. Interactive runs preserve their configured strategy;
explicit factory supports interactive use. The Python API uses the same non-TTY detection unless its caller explicitly
selects interactive or unattended execution. Resume keeps the recorded allocation
and permission decision.

Container mode runs provider help/auth probes inside the pinned image; it needs no
host provider binary. A private account guard requires the corresponding read-only
config opt-in. Host-only delivery still uses host credentials and existing guards.
See [isolated execution](isolation.md) for the complete boundary and degraded fallback.

!!! note "What changes for your workflow"
    Keep the remote base ready for unattended work. Container checks need their
    tools inside your image. Review the frozen mode and image before starting.
