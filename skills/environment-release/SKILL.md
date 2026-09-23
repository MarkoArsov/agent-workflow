---
name: environment-release
description: Release an explicitly selected workflow-owned test environment and its temporary resources.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# environment release

1. Identify the environment and its ownership lease from the current task. Verify that the requesting task owns each process/resource.

2. Run the configured cleanup in the documented order. Stop only owned process groups and remove only task-created disposable resources.

3. Never infer ownership from a port number or stale PID alone. Shared or externally owned infrastructure needs its owner's explicit decision.

4. Recheck health/lease state and report any cleanup failure with the retained resource identity.

