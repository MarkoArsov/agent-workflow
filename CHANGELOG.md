# Changelog

## 0.1.1

- Rename Agent Flow to lowercase plovi across the runtime, installers, CLI,
  discovery, plugin metadata, and documentation.
- Keep `agentflow` and `af-*` as compatibility aliases until 1.0.
- Move project `.agentflow/` configuration to `.plovi/` on first use of the new
  runtime, with recoverable metadata rebasing and no automatic folder merging.
- Preserve existing installation ownership, model settings, and older runtime pins.
- Keep the GitHub repository name, site domain, and visual styling unchanged.
