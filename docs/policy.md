---
title: Project policy
description: Review limits, protected paths, and unattended permissions in plovi.toml.
question: How do I review runner policy?
---

# Project policy

`plovi.toml` lives at the configuration root. Setup includes a commented proposal;
existing projects use defaults until you review a write. Repeated setup preserves
policy comments and edits. Inspect effective values and their sources:

```sh
plovi policy show --json
plovi policy set limits.max_changed_files 60
plovi policy set execution.unattended_permission_mode '"restricted"' --yes
```

`set` shows a diff and validates before saving. Enter a literal `y` interactively,
or pass `--yes` after review. Noninteractive edits require `--yes`. Unsupported
TOML edits and stale previews leave the original file intact. No-op edits preserve
bytes. `doctor` reports missing policy and values duplicated in the profile.

| Key | Default |
|---|---|
| `limits.running_tasks` | 2, reserved |
| `limits.waiting_for_review` | 3, reserved |
| `limits.attempts_per_stage` | 2 attempts per route |
| `limits.max_changed_files` | 40 |
| `limits.max_changed_lines` | 1500 added plus removed lines |
| `limits.size_exempt` | `["**/package-lock.json", "**/*.lock"]` |
| `paths.protected` | `[".github/workflows/**", "**/migrations/**"]` |
| `execution.unattended_permission_mode` | `"restricted"` |
| `autonomy.level` | `"assisted"` |
| `grants` | Empty reserved table |

`ready` and `auto` are accepted autonomy values; they do not enable additional
actions. Slot limits are reserved configuration, not a scheduler. Unknown keys,
unsupported grants, invalid types and repository-escaping globs are errors.

Precedence is per key: explicit plan limits, explicit TOML keys, corresponding
profile values, built-ins. `attempts_per_stage` maps to `attempts_per_route`; it
keeps the existing per-route budget. Policy and permission decisions are frozen
with a run. Review changes and use `resume --rebind` to adopt them. Legacy runs
without a policy binding retain legacy inputs and built-in policy interpretation;
adding explicit policy requires rebind.

## Size and path approvals

The runner measures the cumulative task diff across writable repositories after
code attempts and before delivery. Tracked, untracked, deleted, renamed and binary
files count. Binary files count as one line. Size exemptions cover root and nested
lockfiles; they do not exempt scope or protected paths.

```sh
plovi approve TASK --size
plovi approve TASK --paths --reason "Reviewed migration" --actor "Reviewer"
```

Approvals record identity, reason, time and a path/content/mode fingerprint. The
actor defaults to configured Git identity; supply `--actor` if none exists. Both
gates need approval when both apply. Any diff change invalidates prior approvals.
Resume does not bypass a pending approval, and approval verifies retained stage
output without replaying a successful provider call. Policy inputs themselves
receive no automatic path approval.

!!! note "What changes for your workflow"
    Review policy during setup. When a run pauses for size or protected paths,
    inspect its diff and approve each pending gate. Changes to that diff need a
    fresh approval.
