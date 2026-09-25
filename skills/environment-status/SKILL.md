---
name: environment-status
description: Inspect configured local or shared test-environment readiness and ownership.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# environment status

1. Read the selected environment reference and ownership information. Use its non-mutating health checks and recorded run state.

2. Report service readiness, endpoint, owner, relevant version, and missing dependencies based on observed output.

3. Do not restart, reclaim, terminate, or modify someone else's environment during a status request.

4. If evidence is unavailable, identify the exact missing access or check instead of assuming readiness.

