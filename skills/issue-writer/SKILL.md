---
name: issue-writer
description: Turn an idea, problem, or requirements into well-sized, detailed, test-first issues with dependencies and parallel waves.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agentflow for commands.
<!-- resolver:end -->

# issue writer

Use this skill to turn an idea, a problem report, a feature request, or a requirements document
into one or more tracker issues that a coding agent can implement correctly without coming back
for clarification. Write for a capable but literal implementer that has none of this
conversation's context.

## Understand

1. Resolve the selected tracker, or use Markdown when none is configured. Read the user's input,
   the project instructions (`AGENTS.md`, the workflow profile, design documentation when
   anything people see changes), and the code the change touches. Note current behaviour with
   file paths, function names, and commands.
2. Ask only questions whose answers change scope, behaviour, data, security, or cost, at most four
   at a time, each with options and a recommendation. Everything else becomes a written
   assumption in the issue. Separate facts from assumptions.

## Specify (when the result is more than one issue)

3. Draft a short spec: goal in at most five sentences, users and use cases, numbered
   requirements, non-goals, assumptions, and open questions. Resolve every open question before
   breaking the work down. Keep it in the project's plans directory when one is configured.
4. Record a decision (context, options with trade-offs, choice, consequences) when the change adds
   a dependency, changes a data model or public interface, crosses a security boundary, needs an
   irreversible migration, or has more than one reasonable architecture.

## Break down

5. Size every issue as one pull request that an agent can build and verify end to end in one run:
   a coherent slice of behaviour together with its tests and documentation.
   - Prefer fewer, larger issues. Merge work that touches the same files or the same concept;
     splitting it causes conflicts, repeated context, and integration gaps.
   - Split only when parts can proceed in parallel on disjoint paths, when a contract (schema,
     API, interface, file format) must land before its consumers, when a risky change (migration,
     security boundary) should be isolated, or when the result would exceed the project's change
     size limits or what can be verified in one pull request.
   - Never split code from its tests or documentation, and never create "add tests for X" or
     "document X" follow-ups.
   - Every issue leaves the default branch working and releasable.
6. List each issue's blocking dependencies. Group issues into waves: issues in the same wave have
   no dependency between them and do not write the same files, so they can run in parallel.

## Write each issue

7. Use these sections, in this order:
   - **Why**: the problem or goal, in a few sentences.
   - **Outcome**: what is true when it ships, as user-visible results.
   - **How it works today**: current behaviour with real paths, functions, and commands that you
     read. Omit for new areas.
   - **Scope**: numbered parts with the concrete details an implementer would otherwise guess:
     commands and flags, file and data formats with an example, API shapes, UI states (empty,
     loading, error), exact error messages, edge cases, migration of existing data, and platform
     differences.
   - **Out of scope**: what not to build, with where it belongs instead.
   - **Tests (required)**: test files and concrete cases, the project's helpers and fakes to use,
     fixtures to add. A test that reproduces a bug must fail before the fix. Interfaces people see
     get component and end-to-end tests. No network, real credentials, or real user configuration.
   - **Docs**: pages to add or update, and generated files to regenerate.
   - **Acceptance criteria**: checkboxes; each maps to a test or to a stated manual check.
   - **Pitfalls**: what a less experienced implementer would get wrong here: helpers to reuse
     instead of rewriting, hidden coupling, ordering and crash windows, compatibility, platform
     quirks, names that collide with existing concepts.
   - **Depends on** and **Can run in parallel with**.
   - **What changes for your workflow**: how people's day-to-day use changes, or "Nothing".
8. Put constraints that apply to every issue (runtime dependencies, supported platforms, check
   commands to run, design rules, what the pull request description must list, never weakening
   existing tests) in one shared block appended to each issue, so they read the same everywhere.
9. Do not invent priorities, assignees, estimates, or team identifiers. Keep private identifiers,
   credentials, and machine-specific paths out of issues.

## Check

10. Before showing the set, fix any issue where a "How it works today" claim lacks a real path,
    placeholder text remains, the tests section is empty, an acceptance criterion cannot be
    verified, a dependency points to nothing, or interface work does not reference the design.
11. Show the whole set: titles, dependencies, waves, and complete bodies (or the path of the files
    that contain them).

## Create

12. Creating or updating tracker issues requires explicit authorization for that action and
    content through an available connector or CLI. Without it, or without tracker access, keep the
    issues as Markdown files and say so; do not pretend they were created.
13. When authorized, create issues in dependency order and replace dependency placeholders with
    real numbers. Use labels and milestones only when they already exist or the user asked for
    them. Add a hidden marker such as `<!-- issue-writer: <feature>/<id> -->` to each body and,
    on a rerun, update the matching issue instead of creating a duplicate. When consolidating
    existing issues, edit them in place and close the superseded ones with a comment that links
    the replacement.
14. Report the created or updated issue numbers, the waves, and anything skipped.
