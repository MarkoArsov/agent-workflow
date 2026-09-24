---
title: Keep the workflow clear
description: Change your project's workflow in small, owned, testable steps.
question: How can the workflow itself be changed safely?
---

# Keep the workflow clear

!!! summary "In one minute"
    - Before changing anything, name the problem and find the one place that should own the fix.
    - Project behavior lives in project-owned files: the profile, skill overrides, rules, references, connectors, and stages. Never in installed defaults.
    - A new check may stop runs only when every match is genuinely unsafe or wrong. Everything else is advisory or guidance.
    - Test the change where it runs, and update the guidance people will read.

This page is for whoever maintains a project's workflow. You don't need it for everyday tasks; see the [task lifecycle](tasks.md) for those.

## The simple rule

Answer two questions first:

1. What problem are we solving?
2. Where is the one best place for that rule or behavior to live?

Don't fix the same problem in several places unless those places have different jobs. One source of truth is easier to maintain and doesn't drift.

## Where changes belong

| Change | Where it belongs |
|---|---|
| A fact everyone working in the project needs | `PROJECT_WORKFLOW.md` and your native instructions (`AGENTS.md`, `CLAUDE.md`), outside the managed block |
| One command's behavior | A project skill override: `stageway skill copy NAME` |
| A new command | A new project skill: `stageway skill new NAME` |
| Detailed guidance for one kind of work | `.stageway/references/`, named by the plans that need it |
| A check that can be enforced mechanically | A blocking rule, or a custom stage with completion checks |
| One task's scope | That task's plan: a complete revision, then `resume --rebind` |
| Repositories, commands, routes, or permissions | Setup: re-run it, review the proposal, apply by digest |
| The package itself | [Contribute and develop](development.md) |

## A safe way to make a change

1. **Describe** the recurring problem in plain language.
2. **Find** the file that already owns that part of the workflow. `stageway inspect` and `skill resolve` show the effective sources.
3. **Change** only what is needed to solve the problem.
4. **Document** it where people will look, so the change is discoverable.
5. **Test** it at the level where it runs: a rule against compliant and violating examples, a skill with a small task, a stage with a dry run.
6. **Refresh** host discovery with `stageway refresh` if you added or renamed skills, and apply the reviewed proposal.
7. **Ask** whether the workflow is now clearer and safer. If not, reconsider.

A running task snapshots its configuration, so your change affects the next run. An active run continues with what it bound, until a reviewed `resume --rebind`.

## Adding a recurring rule

Use `add-rule` when the same issue keeps appearing. It helps choose the honest level of enforcement:

| Kind of rule | Best form |
|---|---|
| Every match is clearly wrong, and a command or pattern can find it | A **blocking** rule with a deterministic detector |
| The signal is useful but exceptions are legitimate | An **advisory** rule, recorded with the evidence |
| It needs human judgement | A **prose** rule: short, scoped guidance |

Keep rules as narrow as possible, by path and repository. Record new examples with `stageway rule record RULE --detail "…"`; at the rule's `review_after` threshold, you get a proposal for a corrective review, never an automatic promotion to blocking.
See [rules and references](rules.md).

## Adding or changing a skill

A good skill has one recognizable job. Before adding one, be able to say:

- when someone should use it;
- what it may read and change;
- when it must stop and ask a person;
- what shows it completed successfully;
- what normally happens next.

Extend an existing skill when the work belongs to its job. Create a new skill only for a genuinely different purpose or safety boundary.
Project overrides record the upstream version they came from, and updates report when that upstream changed, so you can merge improvements deliberately.
See [skills and stages](customize.md).

## Before you finish

- The change solves a named problem.
- One source of truth owns the new behavior.
- Related instructions and documentation agree.
- The relevant test, dry run, or rule check has been run.
- Security, testing, and human-approval boundaries are no weaker.
- Advisory findings are not turned into hard stops unless every match is unsafe.
- Another maintainer could understand why the change exists.

<!-- checkpoints: CTX-2, CTX-5, PST-3 -->

## See also

[Skills and stages](customize.md) · [Rules and references](rules.md) · [Checkpoint scorecard](scorecard.md)
