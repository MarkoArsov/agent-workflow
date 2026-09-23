# Test environment lifecycle

Configure environments from the project's real local development commands.
Use disposable resources, explicit readiness checks, and task ownership.

Record the start argv, working directory, timeout, expected readiness signal or
health command, endpoint, and cleanup. Reference credentials through the host or
environment, never a tracked value.

An owning process holds the lease for the environment and terminates only the
children it created. Do not reclaim a shared environment using a stale PID or
port number. Use a named lock when several tasks share one dependency.

Start services before the check that needs them, wait for observed readiness,
run the narrow scenario, and clean up in a finally block. A setup failure is
not red evidence. A readiness check proves availability, not feature correctness.

Keep unchanged companion repositories clean; logs and generated output belong
in ignored directories or disposable temporary folders.
