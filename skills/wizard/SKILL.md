---
name: wizard
description: Guide a bounded manual procedure with explicit prerequisites, evidence, and side effects.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# wizard

1. Identify the exact outcome, environment, authority, and reversible steps. Read existing operational references instead of inventing commands.

2. Prepare a concise checklist with prerequisites, expected output, rollback/cleanup, and the point where external side effects occur.

3. Execute already-authorized local/read-only steps. Ask for only missing decisions or action-specific external permission.

4. Record what was actually completed and preserve useful evidence. Do not imply unattended execution when a human-only step remains.

