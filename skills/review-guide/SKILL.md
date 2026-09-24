---
name: review-guide
description: Walk a reviewer through a completed change in a useful reading and verification order.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# review guide

1. Inspect requirements and the complete final diff. Identify the behavior change, key design decision, risky boundaries, and strongest tests.

2. Create a short reading path through the actual files, explaining what to assess at each point. Group generated/mechanical changes separately only when it helps review.

3. Give reproducible checks and concrete questions for the reviewer. Distinguish observed verification from suggested additional testing.

4. Keep the guide factual and concise; it does not replace independent review or authorize posting it.

