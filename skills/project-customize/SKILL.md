---
name: project-customize
description: Add or modify project skills, scoped rules, references, connectors, and stages.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# project customize

1. Inspect the current project and the requested behavior. Choose the narrowest extension: a skill procedure, scoped guidance, deterministic rule, connector, or ordered custom stage.

2. Use skill copy NAME before changing a bundled skill. Use skill new NAME --description for a new entry, then replace its scaffold with a complete procedure and relevant supporting resources.

3. Keep credentials out of extension files. Reference host authentication or environment variables. Verify headless availability for every selected provider.

4. Custom stages declare an id, exactly one skill or command, inputs, outputs, checks, and before/after position. Keep publication after current verification.

5. Preview refresh and apply only the reviewed proposal. Confirm the generated wrapper resolves to this project's effective source, including detached worktrees.

6. Do not edit installed package files or another project's customizations. Record upstream override differences for review during updates.

