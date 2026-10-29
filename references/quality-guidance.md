# Project quality guidance

Use the project's existing standards and scoped references rather than inventing
one universal coding style. Native instructions and explicit user choices retain
precedence. Language-specific APIs, error mappings, async idioms, nullable context,
test frameworks and environment policies belong to project guidance.

Specify includes this reference itself and applicable project reference names in
the full manifest's `references` list, or names sources explicitly in a manual plan. Project references override
package references of the same relative name. Expose reviewed external guidance
through project-owned references or skill overrides; do not automatically load a
plugin cache, copy a third-party skill body, or require a plugin for every project.
No standards file is mandatory when the project has none.

Implementation, test authoring and review read the same selected guidance. The
runner supplies frozen selected references and project rules to each AI stage.
Do not reload a live override during that run; revisions require the approved
rebind flow. In direct use resolve effective project sources before editing or
reviewing. An explicitly selected missing source is a concrete gap to report, not
permission to silently use unrelated defaults. Keep references focused so review
does not receive an implementation narrative disguised as a quality guide.

Review requirements and observable outcomes first, then behavioral tests,
correctness/failure paths, and project conventions/semantic duplication. Apply
these questions to changed paths without widening the approved scope:

- Do guards enforce the actual contract in both directions? Reject illegal empty
  inputs where appropriate, but verify upstream validation and API guarantees
  before adding or removing redundant/dead checks. Prove a disputed boundary case.
- Are external failures classified from documented or observed error details?
  Distinguish an unexpected response requiring a code fix from a transient or
  operator-repairable outage. Do not assert a domain outcome from status alone
  when the external API uses that status for several causes.
- Do asynchronous operations preserve the language/framework's exception,
  cancellation and resource-lifetime semantics? Apply the project's await policy;
  do not prescribe one syntax across all languages or elide cleanup accidentally.
- Can tests detect swapped concepts because their fixtures use distinct values?
  Consolidate cases differing only in data where the test framework supports it;
  retain separate tests for different concepts/setup/assertions. Assert outcomes,
  including meaningful failures, instead of duplicating implementation details.

Direct review is check-only unless edits were requested. Pipeline review may make
safe in-plan corrections, preserving frozen tests and reverifying affected checks.
Preferences alone are not correctness findings or deterministic blocking rules.
