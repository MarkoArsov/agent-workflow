# Terminal tracking feasibility (2026-11-01)

Primary documentation checked:
- https://learn.chatgpt.com/docs/integrated-terminal
- https://learn.chatgpt.com/docs/developer-commands
- https://code.claude.com/docs/en/vs-code
- https://cursor.com/docs/agent/tools/terminal

The local Codex tool inventory includes opening an app terminal panel and reading
its output. No corresponding command-entry tool was exposed in that inventory.
Opening a panel does not prove a watch command is running. The official integrated
terminal docs describe app actions running in the terminal; a reviewed reusable
action is a possible integration path, to be verified against the host version.

Cursor documents agent terminal execution, which supports use of an existing host
terminal tool; a new dedicated panel still requires a verified adapter contract.
Claude Code CLI can attach a watcher to its current terminal after worker detach.
Its VS Code documentation describes an integrated-terminal CLI and an IDE bridge;
that bridge does not by itself establish an API to create/run a new tracker panel.
Claude desktop, IDE extension, terminal CLI and headless sessions must be treated
as different hosting contexts, even if they use the same provider/model.

Target automatic in-app open-and-run where supported. Minimum correct behavior is
capability detection plus truthful open-only/current-terminal/command-only fallback.
Do not label all three hosts supported until a native smoke records actual tracker
output, no duplicate terminal and worker survival after the viewer closes.

No app UI was opened and no terminal command was injected during planning. Host
support is proposed, not validated. No network listener, app extension or native
agent settings were installed by this research.

## Implementation smoke

The foreground Codex host opened its terminal panel once through its supported
open tool and read the result: an empty terminal snapshot, without command output.
The exposed inventory has no command-entry operation. This proves open-only access
in this session; no tracker was started in that panel. Native Cursor and Claude
VS Code sessions were unavailable for execution smoke and remain unverified. The
always-on disposable tests cover the capability bridge, session acknowledgement,
unknown/closed viewers and command fallback without real model requests.

A disposable POSIX pseudo-terminal smoke also ran the actual pipeline CLI with one
fixture provider request. It observed running and complete human summaries in the
same terminal, a detached worker, one provider call and no duplicate JSON summary.
No real provider generation or native account change occurred. This verifies the
current-terminal path; it does not establish native app command-entry support.
