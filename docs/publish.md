---
description: Prepare and publish a reviewed release of the package.
---

# Publish a release

Publication is a separate maintainer action after local verification.

1. Review the complete diff, local commits, tests, site, and public-content scan.
2. Create the approved GitHub repository and configure its remote.
3. Push the reviewed main branch, then create/push the chosen release tag.
4. In repository Settings → Pages, choose **GitHub Actions**.
5. Run the Pages workflow and check its deployment URL.
6. Verify installation from the published pinned revision in an isolated environment.

The default site is [MarkoArsov.github.io/agent-workflow](https://MarkoArsov.github.io/agent-workflow/).
The v0.1.0 bootstrap expects a matching v0.1.0 tag.

## Custom domain later

Add the domain in GitHub Pages settings and configure DNS according to GitHub's instructions.
Update site_url in mkdocs.yml and any published install/documentation links as needed.
Rebuild and check internal links, assets, HTTPS, and the domain's final URL.

The documentation has no analytics, remote fonts, or runtime connection to local workflow state.
