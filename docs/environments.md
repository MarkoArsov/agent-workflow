# Disposable test environments

A named environment starts owned services, waits for observed readiness, exports connection details to checks, and cleans up even on failure.

Add an environment to the project profile:

~~~json
{
  "environments": {
    "local-app": {
      "lock_id": "sample-local-app",
      "services": [
        {
          "id": "server",
          "repository": "app",
          "command": {"argv": ["python3", "server.py"]},
          "ready_pattern": "^(?P<port>[0-9]+)$",
          "exports": {"SAMPLE_BASE_URL": "http://127.0.0.1:{port}"},
          "startup_timeout_seconds": 30
        }
      ]
    }
  }
}
~~~

This example server prints its assigned port on a line after binding.
Adapt readiness to the service's real output; do not match an unrelated startup message.

A task check selects `"environment": "local-app"` and can reference SAMPLE_BASE_URL through its command's env_refs.
Both service and check repositories must participate in the plan.
Read-only companion repositories stay unchanged.

~~~sh
agent-workflow verify ai-plans/task-name/pipeline.json --phase green
agent-workflow environment status local-app
agent-workflow environment release local-app
~~~

Release asks the owning process to stop its services. It does not kill a saved PID.
Normal completion and failure release the services automatically.

Use the same lock_id when different projects share one local resource.
A second owner is rejected while the lease is held.
Keep logs and runtime output in ignored directories; verification rejects source-changing commands.

These leases manage processes the workflow starts. Existing external infrastructure needs its own documented ownership and cleanup procedure.
