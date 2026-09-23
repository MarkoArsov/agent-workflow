---
name: merge-to-base
description: Perform a separately requested project-enabled local merge with verification and branch guards.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# merge to base

1. Check that the project explicitly enables direct merging and that the user requested this exact merge. Identify source branch, base, and target checkout.

2. Inspect the complete diff, successful current verification, cleanliness, and conflicts. Never merge into a parked checkout while it has user edits.

3. Use the project's configured merge policy. Resolve only understood conflicts within the approved scope and verify the result.

4. Do not push a base branch through the workflow's feature-delivery helper. Any external merge/publish operation requires its own explicit approved procedure.

5. Report the resulting local revision and verification, including whether publication remains pending.

