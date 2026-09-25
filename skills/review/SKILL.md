---
name: review
description: Review requirements against the actual diff, with independent evidence and bounded in-scope correction.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# review

1. Start from the user requirements, native project rules, and actual current diff. Reconstruct behavior from code and tests rather than trusting an implementation summary.

2. Check correctness, regressions, interfaces, tenancy/authorization where relevant, failure handling, test adequacy, and unnecessary complexity. Cite concrete paths and triggering scenarios for findings.

3. In direct review, make no edits unless asked. Prioritize actionable defects; do not invent issues to fill a quota. Distinguish confirmed problems from questions requiring evidence.

4. In a pipeline review, safe corrections within the approved paths are allowed. Preserve assertion-proven tests and the intended design. Changes beyond scope require a revised plan.

5. Run checks affected by corrections and the final named acceptance checks. A changed diff invalidates prior verification. Do not weaken enforcement to finish the stage.

6. Review findings are advisory unless supported by a deterministic blocking guard. Explain severity and user-visible impact without treating stylistic preferences as correctness defects.

7. Do not commit, push, post comments, resolve threads, or request reviews. Draft external feedback when useful; sending requires explicit authorization.

8. Return the requested JSON status and concise factual findings. Report an empty actionable finding set honestly.

