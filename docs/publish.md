---
title: Publish workflow changes
question: How do I publish workflow changes or a release?
description: Publish workflow changes through a pull request, or prepare a reviewed package release.
---

# Publish workflow changes

Run **af-publish-workflow** to collect this workflow checkout's local edits and all commits
missing from the remote default branch into a draft GitHub pull request. A clean working tree
with unpublished commits is supported. The skill resolves the workflow source checkout even
when invoked from an application project; copied installations need an explicit source checkout.

An optional short summary guides the PR title. Use **af-publish-workflow --dry-run** to inspect
the included work, checks, and proposed PR without committing or publishing. A dry run may fetch
remote metadata and run checks. The normal invocation verifies the full change, commits reviewed
edits on a feature branch, pushes normally, and creates or updates the matching PR. Already-pushed
feature commits remain part of that PR until merged. Other local branches are not collected.

This requires Git, authenticated GitHub CLI access, and the checkout's development dependencies.
The command name follows the installed discovery prefix if it is changed. Adding the skill does
not publish anything; publication requires invoking it or explicitly requesting that action.

## Publish a release

!!! summary "In one minute"
    - Publication is a separate maintainer action after local verification.
    - Push the reviewed branch and tag, then deploy this site with GitHub Pages.
    - Verify installation from the published pinned revision in an isolated environment.

Publication is a separate maintainer action after local verification.

1. Review the complete diff, local commits, tests, site, and public-content scan.
2. Create the approved GitHub repository and configure its remote.
3. Push the reviewed main branch, then create/push the chosen release tag.
4. In repository Settings → Pages, choose **GitHub Actions**.
5. Run the Pages workflow and check its deployment URL.
6. Verify installation from the published pinned revision in an isolated environment.

The site is served at [agentic.markoarsov.com](https://agentic.markoarsov.com/), a custom domain configured in the repository's Pages settings.
The v0.1.0 installer expects a matching v0.1.0 tag.

## Custom domain later

Add the domain in GitHub Pages settings and configure DNS according to GitHub's instructions.
Update site_url in mkdocs.yml and any published install/documentation links as needed.
Rebuild and check internal links, assets, HTTPS, and the domain's final URL.

The documentation has no analytics, remote fonts, or runtime connection to local workflow state.
