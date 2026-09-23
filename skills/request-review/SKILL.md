---
name: request-review
description: Prepare a concise review request using the actual PR and verified change summary.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# request review

1. Read the PR, final behavior, checks, and relevant ownership conventions. Identify the requested reviewer only from user input or established project metadata.

2. Draft a short message with the PR link, decision/review focus, and meaningful limitations. Avoid recounting implementation history.

3. Show the exact recipient, channel, and content. Send or assign only when explicitly authorized for that action; a draft PR does not authorize messaging.

4. Report a draft as a draft and a sent request only after a confirmed tool result.

