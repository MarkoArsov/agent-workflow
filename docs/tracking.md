---
title: Tracking a task
description: Follow live work and attach a tracker using the launching host's actual capabilities.
question: How do I follow an implementation run?
---

# Tracking a task

`plovi pipeline PLAN` starts an approved task; `plovi pipeline TASK` continues saved
work. In an interactive terminal it detaches the worker and follows a read-only
watcher. Closing the viewer leaves the worker running. From an agent app, the
foreground skill handles terminal attachment using the returned descriptor.

## Host capabilities

Tracking carries task/run identity, argument array, working directory, runtime
digest and selected mode. Host adapters negotiate only capabilities actually
available in that session; the selected model does not identify the app.

| Host | Measured support | Fallback |
|---|---|---|
| Terminal / Claude CLI | Current-terminal watcher after worker detach; disposable CLI journey tested | Exact command when noninteractive |
| Codex desktop | Local smoke opened the panel and read its empty output; no command-entry tool was exposed | Open-only panel plus exact command; never claimed running |
| Claude VS Code | Capability bridge tested with doubles; native panel execution unverified | Exact command unless a supported host tool acknowledges execution |
| Cursor | Capability bridge tested with doubles; native dedicated tracker execution unverified | Exact command unless a supported host tool acknowledges execution |
| Headless / unknown host | Command descriptor | Exact command |

The [Codex terminal documentation](https://learn.chatgpt.com/docs/integrated-terminal),
[Claude VS Code documentation](https://code.claude.com/docs/en/vs-code), and
[Cursor terminal documentation](https://cursor.com/docs/agent/tools/terminal)
describe terminal facilities. Their existence does not establish a universal API
for a Python worker to open and run a panel. No cross-host native open-and-run
support is claimed by this release.

With `open_and_run`, an adapter needs a nonempty session handle and a running
acknowledgement before reporting attached. `open_only` reports opened and supplies
the command. Saved handles require a liveness probe before reporting still attached;
unknown liveness reuses the handle without opening duplicates and reports
unverified. A confirmed closed viewer may be replaced. Viewer errors never launch
another worker, cancel one, or consume model attempts. UI calls stay in the
foreground host, respecting its permission controls.

## Human and machine output

```sh
plovi status TASK
plovi watch TASK
plovi watch TASK --seconds 60
plovi watch TASK --json
```

Human output shows task, stage, status, elapsed time, selected provider/model, and
age of the last provider/tool activity. Workers pulse every 15 seconds. Inactivity
warnings precede bounded watchdog stops. Long tools and quiet providers remain
distinct from a stopped worker.

`--json` emits version 1 objects with `type` equal to `summary` or `event`.
Summaries contain compact status/completed stages, question/approval/escalation
when present, run identity and activity timestamps. Events contain run identity,
monotonic sequence, UTC timestamp and event name, plus stage/attempt/check metadata
when applicable. Ordinary output excludes baseline maps, prompts and full tool
output. Use `status --verbose --json` deliberately for detailed state.

Events are redacted JSON Lines in `events.jsonl`; one previous segment is retained
at a one-megabyte rotation threshold. Consumers use file identity, byte offset and
sequence cursors, tolerate incomplete trailing records, and ignore duplicates.
Slow observers may miss retired history; the atomic live and status summaries
provide current status without reloading the large baseline journal. Heartbeats show worker liveness, not verified implementation progress.
