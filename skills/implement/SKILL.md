---
name: implement
description: Implement an approved change and complete the named verification and correction loop.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# implement

1. Read the complete plan, project workflow, native instructions, and nearest established implementation. Follow the planned repository membership and path boundaries.

2. Use the current checkout or prepared task worktree. Read-only companion repositories supply context and checks; do not branch or edit them.

3. Implement the smallest complete change that satisfies the requirements. Handle authorization, data boundaries, failure modes, compatibility, and migrations where the project requires them. Avoid opportunistic refactors.

4. Preserve independent tests. Do not weaken, skip, remove, or rewrite assertion-proven tests to make results green. A wrong test or changed requirement needs a complete plan revision and renewed red evidence.

5. Run each named check in its configured working directory. Diagnose failures, fix the cause, and repeat only relevant checks. Finish with all acceptance mappings evidenced against the current diff.

6. Inspect the final diff for accidental files, credentials, unrelated formatting, and generated artifacts. Follow project rule detectors and scoped references.

7. Do not perform runner-owned commit/push/PR mechanics. In direct use, separate completion from any unrequested delivery action.

8. When blocked by a concrete missing decision or inaccessible dependency, state exactly what is needed and why. Do not invent credentials, silently omit checks, or claim success from an agent narrative.

9. Return complete only when implementation is ready for independent checks; include any material limitations. The runner validates outputs and may return observed failures for correction.

