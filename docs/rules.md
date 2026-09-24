---
title: Rules and references
description: Add scoped project conventions and bring relevant guidance into tasks.
question: How do I capture project conventions and load the right guidance?
---

# Rules and references

!!! summary "In one minute"
    - Rules are blocking, advisory, or prose. Blocking needs a deterministic detector.
    - Built-in scope, secret, and delivery guards are always blocking.
    - `rule record` counts recurring examples and proposes a corrective review at a threshold; it never promotes a rule by itself.
    - References hold reusable guidance; a plan names the ones its stages need.

Rules live in the configured project rule directory. Give each rule a stable ID, useful guidance, and relevant paths.

~~~json
{
  "id": "explain-compatibility",
  "enforcement": "prose",
  "paths": ["src/**"],
  "guidance": "Explain compatibility consequences when changing a public interface.",
  "review_after": 3
}
~~~

## Choose honest enforcement

| Class | Use |
|---|---|
| Blocking | A reliable command or forbidden-pattern detector identifies a concrete violation. |
| Advisory | A useful signal needs judgment. |
| Prose | The convention depends on context and examples. |

Test blocking rules with both compliant and violating examples.
Built-in scope, secret-material, and delivery guards remain blocking.

Record recurring examples with `rule record RULE --detail "Observed example"`.
At the configured threshold, the result proposes a corrective review.
It does not automatically turn a nuanced convention into a fictional deterministic detector.

## Load relevant context

Keep reusable project explanations under the references directory.
A task's `references` list names the guidance needed for its stages.
Native instructions retain authority.

Use **prune-context** to propose removing duplication or obsolete detail.
It makes a reviewable proposal; it does not silently delete guidance.

<!-- checkpoints: CTX-4, CTX-5, PST-3, VER-6 -->
