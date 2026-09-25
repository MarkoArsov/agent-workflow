---
name: add-rule
description: Capture a recurring project convention with appropriate enforcement and a reviewable example.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# add rule

1. Inspect the recurring issue and nearest established patterns. Describe the desired behavior, affected paths, and concrete positive/negative examples.

2. Choose blocking only when a deterministic command or forbidden-pattern detector is reliable. Use advisory for useful imperfect signals and prose for context-dependent judgment.

3. Write a project rule declaration with id, guidance, scope, enforcement, detector when applicable, and review_after threshold.

4. Test a blocking detector against both violating and compliant examples before enabling it. Avoid creating a detector that merely matches one historical incident.

5. For repeated prose violations, record examples and propose a corrective review: improve guidance, scope, examples, or checkpoints; automate only what can be checked honestly.

6. Show the proposed rule and expected impact. Preserve existing project conventions and do not modify package defaults.

