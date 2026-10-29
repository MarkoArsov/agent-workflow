# Skill procedure walkthroughs and fixture evidence

These are manual walkthroughs of the revised effective skill, not independent
live-agent runs. They assess whether its instructions resolve realistic choices;
they do not prove that every future model will follow prose. No additional provider
session was started for evaluation because this task uses manual implement only.

| Input | Walkthrough result | Readiness/authorization boundary |
| --- | --- | --- |
| Add lineage selection and benchmark evidence | Substantive runtime work defaults to full planning | Four documents and manifest, selected checks/routes, actual validate-plan/preflight results, then approval |
| Fix a short behavioral bug in an existing function | Prompt length and a local pattern do not justify manual execution | Record expected behavior, reproduction, evidence-based cause/scope and meaningful regression; full by default |
| Correct one typo in a guide | Trivial low-risk wording exception permits manual | State why the exception applies and name a relevant documentation check |
| Implement the substantive model change manually | Explicit user choice wins | Implement owns tests/code/checks in session; no detached manifest is required |
| Full task has no available model route | Preserve full draft and identify the exact route gap | Do not claim readiness, fabricate access, drop stages or choose manual to bypass it |
| Extend an already approved task with a substantive new requirement | Preserve the prior complete plan and update current artifacts coherently | Prior approval covers its scope only; obtain approval of the revision before implementation |
| Task already has a worktree | Reuse it before writing plans | Record canonical configuration root and pass --project at handoff; avoid copied-profile nesting |
| Two concurrent tasks share a repository | Use separate task worktrees under configured policy | Branches in one directory do not isolate files; preserve task/branch ownership |
| Selected shared checkout is dirty/staged | Inspect and identify ownership before any switch | No automatic stash/reset/moving edits; ask only for a genuinely missing choice |
| Project explicitly uses current-checkout | Honor the policy | Do not force a new branch/worktree or move existing plans |
| Multi-repository parent has a shared plan store | Use the configured owner/shared location | Never initialize a Git parent or branch read-only companions just to store plans |

Observed executable fixture evidence is separate from these judgments:

- WorkflowPracticesTests.test_task_checkout_can_precede_manifest_and_is_reused
  creates a real temporary task worktree before any manifest, writes the plan
  there, resolves the canonical project explicitly, reuses the same checkout and
  proves a second task has a distinct directory without that plan. The parked
  branch remains unchanged.
- test_shared_reference_is_frozen_for_all_ai_stages proves selected guidance
  reaches all three AI stages, live replacements/unselected references stay out,
  and independent review excludes implementation reasoning. Missing requested
  guidance raises the existing concrete error.
- test_retro_discovery_is_overridable_and_project_local proves catalog discovery
  and per-project override precedence. Existing install/release tests validate
  generated discovery and portable payload relocation with the new skill included.

## Fictional retrospective walkthrough

Input classification was performed manually on these fictional events:

1. “You used the target code as the source; the fixture made them identical.”
   A genuine correction. A temporary Git fixture's cached origin/main still has
   identical source/target values, so the premise survives. Proposed home: its
   tracked quality guide, with a behavioral swapped-field regression as the
   preventive check. This is one proposal, not an automatic edit.
2. “Make the theme dark now.” A new direction, not a prior agent mistake; drop it.
3. “Add a timeout to external requests.” The fixture's cached origin/main quality
   guide already requires a bounded timeout. Mark that guidance candidate covered;
   further behavioral verification would be needed before alleging enforcement
   is broken. Do not duplicate the rule.

The fixture was created in an isolated child environment with fictional Git identity
before analysis. Premises were read with git show against a local remote-tracking
reference; status was unchanged afterward. There was no network fetch or claim
about live upstream freshness. No PR-thread pass was requested or performed, and
no analyzed source/guidance was edited. Saving this task's evaluation record is part
of the approved implementation plan, not an implicit write from invoking retro.
