---
description: Review changes and complete the delivery steps selected for a task.
---

# Review and delivery

**review** starts from requirements and the actual diff.
Direct review is check-only unless edits are requested.
Pipeline review may make safe corrections within scope, followed by current checks.

## Deliver selected repositories

The runner owns commit, push, and draft-PR mechanics.
It stages task-owned paths, uses the approved message, pushes the explicit feature branch, and reuses a matching open PR.

It refuses base-branch delivery, force pushes, unrelated staged changes, and pre-existing user changes.
Repositories are independent: if one push fails after another succeeds, status records the partial result.
Resume continues from recorded commits and pushes.

## PR feedback and bots

**address-pr-comments** retrieves paginated issue comments, review comments, reviews, and thread state.
Fix selected issues, verify, and draft factual replies.

CodeRabbit and Bugbot feedback can be polled for a bounded number of rounds.
Temporarily changing a draft to ready needs explicit authorization; its draft state is restored even if retrieval fails.
No bot-control comments or thread resolutions are sent implicitly.

## Everyday tools

Use **peer-pr-review** for another author's change, **diagnose-ci** for a specific failed run,
and **pr-preflight** before delivery.
**commit**, **push**, **worktree-start**, and **sync-base** remain available independently.

[Full skill reference](generated/skills.md) · [Recovery](recovery.md)
