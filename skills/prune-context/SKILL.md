---
name: prune-context
description: Propose evidence-based instruction pruning while preserving meaningful project safeguards.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# prune context

1. Read the selected instruction/reference files and recent examples supplied by the user. Identify repetition, contradictions, obsolete steps, and misplaced detail.

2. Keep root guidance compact and move scoped details to relevant references where appropriate. Preserve safety, compatibility, and repository membership rules.

3. Prepare a diff/proposal explaining each removal or relocation with evidence. Do not delete instructions merely because they are long or rarely triggered.

4. This skill is proposal-only unless the user explicitly authorizes applying the concrete changes.

