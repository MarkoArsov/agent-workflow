---
title: Checkpoint scorecard
description: Stagecoach measured against 36 verification checkpoints, gaps included.
question: What does Stagecoach cover, and what is still open?
footer: reference
footer_order: 3
---

# Checkpoint scorecard

!!! summary "In one minute"
    - This is an assessment, not a sales document. Each of the <!-- scorecard: total --> checkpoints from [the verification gap](why.md) gets one honest status.
    - <!-- scorecard: count implemented --> are implemented, <!-- scorecard: count partial --> are partial, and <!-- scorecard: count conditional --> apply when a plan selects them. The rest belong to your organization, are deliberate policy choices, or are open gaps.
    - The largest gaps are operating-system isolation, network egress, and scoped credentials. See the [open frontier](#the-open-frontier).
    - Every row cites the files that implement it, and the build checks that those files exist.

Most tools tell you they're safe. Stagecoach publishes the scorecard: what the runner enforces, what's partial, what belongs to your organization, and what's still open.

<!-- scorecard: grid -->

## Status language

| Status | Meaning |
|---|---|
| Implemented | The runner or a maintained skill enforces it and records evidence. |
| Conditional | Enforced when the plan selects it. |
| Partial | Addresses part of the checkpoint; a material gap remains. |
| External | Belongs to source control, identity, or organizational operations. **External is not a pass**; it needs its own evidence. |
| Gap | Not provided by the current execution environment. |
| Policy choice | A deliberate design choice that differs from the checkpoint. |

## At a glance

<!-- scorecard: glance -->

<!-- scorecard: phases -->

## Beyond the rubric

Some controls matter precisely because agent execution is stateful, fallible, and easy to misrepresent. The rubric doesn't name them, but Stagecoach relies on them.

<!-- scorecard: beyond -->

## The open frontier

These are the next engineering problems, stated plainly. They are also where [contributions](open-source.md#contribute) help most.

<!-- scorecard: frontier -->

## See also

[The verification gap](why.md) · [Security boundary](security.md) · [How it's tested](coverage.md)
