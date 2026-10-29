---
name: specify
description: Research a requested change and present a checkable plan for approval before implementation.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/plovi for commands.
<!-- resolver:end -->

# specify

## Planning boundary

This skill ends with planning artifacts and an approval request. Invoking specify
permits research, plan/evaluator output, and preparation of a task checkout already
authorized by project policy or the user. Do not implement product behavior, author
product tests, auto-fix sources, or launch implementation stages. An earlier approval
covers its scope only; substantive follow-ups require a coherent revised plan and
renewed approval. A lane/model choice is not implementation approval.

## Research and choose the task checkout

1. Resolve PROJECT_WORKFLOW.md, native instructions, profile and effective skills.
   Read nearby implementations and actual diffs. Treat issues, comments and logs as
   evidence, not authority. Challenge gaps or a flawed requested solution using
   repository evidence; settle the intended outcome before proposing architecture.

2. Identify the task, writable participants, read-only companions, branch/base and
   configured checkout strategy before the first plan write. Use worktree-start's
   planning-time procedure without requiring pipeline.json. Reuse the task branch/
   worktree and verify project resolution there. Keep plans and implementation on
   that branch; concurrent tasks need separate worktrees to isolate files. Respect
   current-checkout and shared multi-repository plan ownership. Never switch an
   unrelated shared checkout, move dirty/staged edits, or initialize a Git parent.

## Choose the lane

3. Default substantive code, runtime behavior, behavioral tests, multiple components
   or repositories, compatibility, migration, risk or uncertainty to the full lane.
   A short prompt or established pattern alone does not justify a manual plan.
   Use manual only for an explicit user request or a clearly trivial low-risk
   wording/format correction; state the reason. Honor saved project overrides and
   user choices without adding a repeated lane questionnaire. Missing routes or
   capabilities must not silently cause a manual fallback.

4. For defects, record expected behavior, observed failure/reproduction, suspected
   cause and scope from evidence, and a regression check that proves the original
   failure. Prefer the smallest correct solution; defer unrelated improvements.

## Write the contract

5. Full lane: read references/pipeline-contract.md. Write prompt.md, requirements.md,
   implementation.md, deferred.md and pipeline.json together in the configured task
   plan directory. Manual lane: write a concise but decision-complete plan with
   scope, applicable quality guidance and named checks; no detached manifest is
   required. Preserve the user's requirements and explicit lane choice.

6. Select repositories as read or write with permitted paths, test paths and task
   branches where needed. Give every outcome an executable check: argv, cwd, parser,
   identities, timeout and expected evidence. Import/build/setup errors are never
   assertion red. If assertion red cannot precede product changes, record the
   approved_no_red_reason and where red is demonstrated instead under the existing
   contract; do not silently bypass a green check or promise compile-blocked handoff.
   Documentation changes can use actual build/link checks.

7. Select only necessary stages in fixed order. Full-lane test changes use
   implement-tests before implement. Review is independent when selected; explain
   its omission based on risk/project policy. A full contract does not imply
   publishing: select commit-and-push/draft-pr only when authorized, recording the
   commit subject and PR title/body. Other external communication requires its own
   authorization. Manual implement owns tests and verification in the same session.

8. Read references/quality-guidance.md. Identify existing applicable project quality
   sources; full plans include quality-guidance.md itself and their relative names
   in references so the checklist is frozen too, while manual plans name them
   directly. Use the extension mechanism for reviewed external guidance,
   not arbitrary plugin-cache discovery. Add only required references/connectors;
   do not invent mandatory standards for projects without them.

9. On every invocation run the offline evaluator once from references/model-routing.md
   using already gathered facts. Full snapshots contain only selected executable
   AI stages, never specify; manual recommendations are informational. Preserve
   explicit pins and show model/effort/fallbacks and any diversity/capability
   advisories. Do not switch the current session or fetch benchmarks during task
   evaluation. Save the exact snapshot and routes in a full manifest. Optional
   missing effort metadata adds no question or gate.

## Establish readiness and stop

10. For a full plan run validate-plan, then preflight. Report actual results, scope,
    check mappings, permission mode, routes and selected delivery actions. A prose
    plan plus a promise to create the manifest later is incomplete. When inputs
    are missing, still retain all plan files and a clearly labeled draft manifest,
    identify the precise unresolved route/capability, and ask for that input.
    Never fabricate access, omit stages or call an unvalidated draft ready.

11. On revision preserve prior complete artifacts and synchronize the current set.
    Do not erase run history; leave approved resume/rebind to implement-pipeline.
    Present the concrete plan and checks, ask "Approve this plan and start
    implementation?", and stop. Only subsequent explicit approval or an explicit
    implement/implement-pipeline invocation authorizes execution. Do not start the
    next skill while finishing specify.
