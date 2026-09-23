# Connectors

GitHub uses the authenticated `gh` CLI.
Linear, Notion, and other services use a host connector or a project command transport.

Declare capabilities and availability instead of assuming one universal tool name:

~~~json
{
  "id": "tracker",
  "transport": "host",
  "capabilities": ["read:issue"],
  "providers": {
    "claude": {"headless": true, "tools": ["your-configured-issue-reader"]},
    "codex": {"headless": false}
  }
}
~~~

Place the declaration under `.agent-workflow/connectors/`.
The availability entries are your verified configuration, not an automatic discovery guarantee.
A connector that works in an interactive host may be absent in its headless CLI.

## Command transport

Declare `transport: command` and a command object.
The runtime sends a JSON object containing capability and payload through stdin.
Only declared read capabilities can be invoked through `connector read`.
Credentials stay in referenced environment variables or the tool's login state.

## Configure a host

`connector preview` prepares a JSON MCP patch while preserving unrelated settings.
Review the target, exact server configuration, and diff before using `connector apply --approve`.
The helper supports JSON `mcpServers` configuration; use the provider's native settings workflow for other formats.

## External actions

Reading and local drafting follow the task.
Posting comments, resolving threads, messaging, creating issues, and changing tracker state need authorization for that action and content.
Selecting commit/push/draft-PR stages authorizes those delivery actions only.

Missing access has an explicit alternative: Markdown issues/plans and no tracker.
