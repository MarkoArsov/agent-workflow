---
description: Configure commands, permissions, and provider routes for checked work.
---

# Commands and permissions

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
| Claude | --dangerously-skip-permissions | dontAsk with an explicit allowed_tools list |
| Cursor | --force, --sandbox disabled, --trust | --sandbox enabled, --trust |

The runner checks installed flags before execution. Unsupported controls stop preflight.
Restricted Claude requires `execution.provider_settings.claude.allowed_tools`.
Use only the tools the task actually needs.

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
