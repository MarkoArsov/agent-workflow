---
title: Isolated execution
description: Task worktrees by default, opt-in factory checkouts and an optional container boundary.
question: How do I keep unattended work away from my checkout?
---

# Isolated execution

Every run uses each repository's configured checkout strategy: the task's own worktree
by default. Factory checkouts are opt-in: set `isolation.checkout = "factory"` in
`plovi.toml` to give detached, unattended and non-TTY runs independent factory checkouts,
or choose `factory` during setup to use them interactively too. Resume always keeps the
saved allocation.

## Factory checkouts

plovi creates an independent bare mirror from each selected repository's effective
fetch URL under the user data directory:

```text
projects/<project-id>/
  origin.json
  mirrors/<repository-id>.git
  allocations/<task>.json
  worktrees/<task>/<repository-id>/
```

Each new task refreshes the remote base under a shared lock. Its receipt pins the
base commit. When the task already has its own `task start` branch, as every task
planned with specify does, the factory branch starts from that branch's committed
head instead, so the plan commits reach the pull request. The commit the task
started from must already be on the remote base; plovi refuses unpushed base
commits and an uncommitted plan, and never copies uncommitted files.
`preflight` and `run --dry-run` only report the strategy; the checkout is created
when the run starts. Refresh updates remote-tracking refs and preserves active task heads.
Your clone's dirty files, index and branch can change while the task runs. Selected
read-only companions also get detached factory checkouts at their remote base.

Configure a real fetch/push remote and an existing remote base before starting.
Keep passwords and tokens out of remote URLs; use a host credential helper.
Changed project IDs or URLs, incomplete mirror creation and unowned task paths
stop allocation rather than adopting existing files. Host delivery checks the real
push identity and pushes an explicit task branch. It never pushes the mirror.

`plovi worktrees` includes local and factory allocation records, ownership and mode.
`plovi clean --older-than 7d` removes only owned, unlocked, clean worktrees with
recorded cancelled, merged or closed state. The age starts at the recorded terminal
time; omit the flag for no age restriction. Complete, failed, paused or escalated
alone never qualifies. Unknown and unpushed work stays available for recovery.
Cleanup preserves mirrors, branches, receipts and evidence and never queries a tracker.

## Experimental container mode

Container execution supports macOS and Linux with a local Docker or Podman engine.
It requires factory-owned checkouts, including for interactive runs: set
`isolation.checkout = "factory"`, or validation stops with "Container mode needs
isolation.checkout = "factory"". An existing
local allocation needs a fresh task; resume never relocates or remounts it.

Review these values together in `plovi.toml`:

```toml
[isolation]
mode = "container"
runtime = "auto"
image = "plovi/runner:local"
network = "on"
mount_harness_config = []
api_key_env = []
```

`mode` defaults to `none`; `runtime` accepts `auto`, `docker` or `podman`. Auto
probes Docker then Podman with bounded waits. Image is required for container mode.
Preflight inspects the local image, pins its immutable ID and probes the selected
harnesses inside it. No host provider CLI is required for contained execution.
Missing images never pull automatically. After reviewing the image, a one-time
`plovi run PLAN --pull-isolation-image` permits pulling the named image.

Build your image before the run. Start from `templates/isolation/Dockerfile`, which
contains Git and Python. Add the exact harness versions and language tools your
project needs using their official installation instructions. For example, a
Node-based CLI needs Node and its package manager before installing the selected
CLI; a .NET check needs the matching SDK. Test their `--help` commands in the image.
plovi does not install toolchains, publish images or update your image automatically.

Every agent attempt, custom command stage, named check, `verify` and check service
uses the boundary. Prompts enter over stdin. The runner, path/evidence guards,
commits, pushes and pull-request calls stay on the host. Do not put host-only build
paths in check argv: tools and project paths must exist inside the selected image
and mounted task tree.

Only selected task checkouts and their required mirrors are project mounts:
writable repositories are read-write, companions and mirror Git metadata are
read-only, at identical absolute paths. The user's checkout, package root, home,
evidence directory, SSH agent and engine socket are not mounted. Git status, diff
and other reads use optional locks disabled and exact safe-directory entries.
Git metadata writes fail inside the container; delivery belongs to the host runner.

Each invocation uses `run --rm --pull=never`, an explicit working directory, stdin
and no TTY. Linux maps the host UID/GID; rootless Podman uses keep-id. HOME is a
fresh container-only temporary directory; PATH comes from the image. The host
allowlist forwards LANG and only explicitly named API variables. Reviewed service
leases can also supply their generated endpoint variables. Image-defined
environment defaults are outside this host allowlist guarantee.

To use a login, opt into each provider config separately with
`mount_harness_config = ["codex"]`, for example. Those specific directories mount
read-only under temporary HOME. There is no broad home fallback and no host config
write. A configured private Claude account guard must be verified inside the same
selected config mount. API keys pass by name from a sanitized engine-client
environment, never as argument values or key files. Their values are not frozen in
bindings or evidence. Mounted login tokens and allowlisted API keys are readable
by the agent: use appropriately scoped credentials.

## Network, services and recovery

`network = "off"` uses the engine's network-none mode. It normally prevents hosted
provider calls and package downloads too. Network on provides ordinary engine
networking, without egress filtering. Shared check services need network on and
use a task-scoped runtime network. Bind services to their container interfaces and
use their configured service ID as the network hostname in exported URLs. Cross-
container service requirements with network off stop before stage execution.

Cancellation, timeout and stalled tools explicitly remove only owned containers;
killing the engine client alone is insufficient. Interrupted-run recovery cleans
the saved owned resources under the task lock before another provider attempt.
Task networks are removed with their services. Cleanup failures stop recovery.

Unavailable runtime or images stop trusted execution before a stage. Restricted
execution can use a saved, displayed degraded host boundary for those availability
failures only. Invalid policy, invalid image metadata, failed account verification
and failed contained commands never trigger host retries. Windows container mode
reports unsupported; restricted host fallback says so explicitly. Factory checkouts
remain portable independently of container support.

Factory checkouts protect your checkout from accidental task edits; they are not
an operating-system sandbox. Provider restrictions remain provider-specific.
Container mode adds a filesystem/process boundary, but writable workspace content
can still be destroyed or delivered incorrectly. It does not protect against a
hostile engine or image, filter egress, or add isolation to mode none.

The default suites simulate Docker/Podman; they do not prove containment. The
separate `PLOVI_TEST_DOCKER=1` smoke needs a prebuilt local image, uses network off
and no credentials. Real-engine validation remains a separate opt-in check.

See the [Git mirror documentation](https://git-scm.com/docs/git-clone),
[Docker run reference](https://docs.docker.com/reference/cli/docker/container/run/)
and [Podman run reference](https://docs.podman.io/en/latest/markdown/podman-run.1.html).

!!! note "What changes for your workflow"
    Push the intended base before unattended work and inspect its factory checkout.
    To add a container boundary, review the policy and build a local image with
    your tools. Keep login/config mounts opt-in. Resume uses the original checkout
    and frozen image; host delivery keeps the existing evidence and approval guards.
