Closes #18.

## What changed

- An append-only ledger in your user data folder records every run, stage,
  attempt, question, approval, escalation, delivery, pause, cancel and policy
  change, with who did it and why. `state.json` is now a cache that
  `plovi rebuild-state <task>` restores from the ledger.
- One operations layer is the only way to change state. `plovi commands --json`
  lists every operation with its arguments, whether it changes anything, and its
  risk. High-risk operations preview first and apply by digest.
- `plovi inbox` lists everything waiting on a person, oldest first, each with the
  command that resolves it.
- `plovi projects add|list|remove` registers the projects plovi manages; setup
  registers new projects automatically.
- New `pause`, `events`, `answer --text` and `approve --plan` commands.
- New `plovi-factory` skill: how an agent operates plovi through these commands.

## Tests added

The implementation stage replaces this section with the exact files, case names
and results from the final evidence.

## Commands run

The implementation stage replaces this section with the actual commands and
results: unittest discover, mkdocs build --strict, check_links site,
generate_docs --check, check_public_content --history.

## What changes for your workflow

- New daily loop: `plovi inbox` shows what needs you; resolve items with
  `plovi answer`, `plovi approve`, `plovi retry` or `plovi resume`.
- You can ask any agent session to "check the plovi inbox" or "retry 146 with
  this note": it uses the `plovi-factory` skill.
- Runs you start yourself (`plovi run`, `plovi pipeline`, resume, answer, retry)
  record the plan approval automatically. Background workers refuse a plan whose
  hash has no recorded approval; approve one with
  `plovi approve <task> --plan --approve <sha>`.
- Run history now lives in your user data folder and survives deleting the
  project's local folder.
