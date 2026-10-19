---
name: publish-workflow
description: Publish unpublished workflow-package commits and local edits together through a GitHub pull request.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agentflow for commands.
<!-- resolver:end -->

# publish workflow

Use this skill when the user requests publication of changes to the workflow package itself.
An invocation authorizes committing the selected checkout's workflow edits, pushing a feature
branch, and creating or updating its draft PR. A request to create, install, explain, or modify
this skill does not authorize publishing. `--dry-run` prepares the inventory, checks, and PR text
without staging, committing, switching branches, pushing, or creating/updating a PR.

## Resolve the workflow checkout

1. Use the selected package root returned by the resolver, not the calling application's Git
   repository. Verify that `git rev-parse --show-toplevel` equals that package root and that it
   contains `workflow-package.json`, `runtime/agentflow`, and `skills`. Read its `AGENTS.md`.
   A copied installation is not the source checkout: if it has no repository of its own, ask for
   the workflow source checkout. Never initialize Git in an installed payload or publish a parent
   repository. An explicitly supplied checkout must satisfy the same checks.
2. Resolve the GitHub repository, publishing remote, and remote default branch from Git/`gh`
   metadata. Do not hard-code an owner, repository name, package brand, or `main`/`master`. Use
   `origin` when it unambiguously identifies the publishing repository; ask if fetch/push URLs
   disagree or multiple destinations/forks make the target ambiguous. Show the resolved target.
   Fetch the selected remote's branches and resolve its current default branch before comparing.
   Never replace an existing remote or create a remote repository implicitly.

## Collect all unpublished work

3. Inspect the current branch, merge/rebase/conflict state, staged and unstaged diffs, and
   non-ignored untracked files. Use NUL-delimited Git output when collecting paths. Inspect
   `git log <remote>/<base>..HEAD` and `git diff <remote>/<base>...HEAD` as well as local edits.
   Include local commits even when the working tree is clean. Compare against the PR base,
   not just the branch's upstream: commits already pushed to a feature branch still belong in
   its unmerged PR. Do not combine unrelated local branches or worktrees automatically.
4. Review the entire outgoing commit range and local edits for workflow scope and public content,
   including deleted/renamed files and intermediate commits. Exclude credentials, private project
   data, local installation receipts, runtime state, caches, and generated site/build output.
   Do not silently publish or discard suspicious/unrelated changes: explain the specific conflict
   and obtain a scope decision. Do not use blanket `git add -A`; stage only the reviewed paths.
   Stop for unresolved conflicts or an in-progress Git operation. Preserve existing staged work.
5. Resolve base divergence without rewriting local history. If the remote base is not an ancestor
   of HEAD, reconcile it on a feature branch with a normal merge and revalidate the combined
   changes; ask for any material conflict decision. In a dry run, only report the required merge
   and the checks that must be repeated afterward; do not merge or switch branches.
   Never reset, rebase, cherry-pick, or force-push
   merely to make publication succeed. Detached HEAD needs an explicit branch choice. If there
   are no local edits, outgoing commits, or existing PR to report, return "Nothing to publish."

## Verify and publish

6. Run the checkout's required checks for the complete outgoing change, including its test suite,
   generated-document freshness, strict documentation build/link checks, and public-content scan
   when supplied. Reuse observed successful evidence only when it applies to the exact current
   contents. Report failures honestly and fix only in-scope issues; do not publish failing changes
   or claim that a content scanner proves the absence of secrets. Write a concise title and body
   from the complete base-to-head change plus local edits, with actual validation results.
   An optional user summary guides the title; otherwise derive it from that complete change.
7. Show the target, base, included commits/files, feature branch, checks, and proposed PR text.
   Explicit publication already authorizes these ordinary actions; ask only for unresolved scope
   or destination choices. For `--dry-run`, stop here. From the default branch, create a new
   `codex/publish-workflow-<summary>` branch at the current HEAD, preserving every unpublished
   commit. Reuse the current feature branch when it contains the selected work and is safe to push.
   Check local and remote branch-name collisions and existing PRs before pushing. If the branch's
   prior PR was closed or merged, resolve whether to use a new branch/PR first. Never overwrite
   an unrelated branch.
8. Commit the reviewed local edits on the feature branch, leaving existing commits intact. If
   there are only unpublished commits, do not manufacture an empty commit. Recheck HEAD, index,
   working-tree scope, and the final base diff before pushing; unexpected concurrent edits require
   a fresh review. Run a normal push with an explicit `HEAD:refs/heads/<feature>` destination.
   Never push to the default branch, force-push, tag a release, merge a PR, or deploy the site.
9. Find an open PR for the exact repository, head branch, and base before creating one. Reuse it
   and update its title/body to cover the full change; preserve its current draft/ready status.
   Create a draft PR if none exists. Multiple matches or a previously closed/merged head branch
   require resolving the branch/PR choice first. Use a temporary UTF-8 body file with
   `gh pr create/edit --body-file`, not shell-interpolated multiline text. Do not add reviewers,
   post comments, or update an issue tracker implicitly. Attach the created/reused PR to this
   chat when the host provides a PR attachment tool.
10. Verify and return the PR URL, branch, included changes, and check results. On partial failure,
    report the last completed step and preserve all commits and edits. A retry must inspect the
    existing remote branch and PR before continuing, so it neither duplicates a PR nor rewrites
    already published history.
