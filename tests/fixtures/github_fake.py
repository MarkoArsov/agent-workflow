#!/usr/bin/env python3
"""Offline, stateful GitHub CLI fake for tests.

It does only what a test scripted in the state file at PLOVI_TEST_GITHUB_STATE.
Every call is appended to <state>.calls.json. A call no handler maps exits 99
and prints its argv, so a test that reaches new GitHub behavior fails loudly.
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

UNMAPPED = 99
HOST = "https://example.invalid"


class Unmapped(Exception):
    pass


class Failed(Exception):
    """A scripted GitHub error: printed to stderr, exit 1."""


def empty_state():
    return {"repo": "example/fixture", "viewer": {"login": "fixture-user", "type": "User"}, "next_number": 1,
            "issues": {}, "pulls": {}, "checks": {}, "statuses": {}, "collaborators": {},
            "actions": {"runs": [], "jobs": {}, "artifacts": {}, "logs": {}}}


# ---- argv helpers ----------------------------------------------------------------

def option(argv, *names, default=None):
    for name in names:
        if name in argv:
            index = argv.index(name)
            if index + 1 >= len(argv):
                raise Unmapped()
            return argv[index + 1]
    return default


def fields(argv):
    """-f/-F/--raw-field/--field values as a dict."""
    result = {}
    for index, word in enumerate(argv):
        if word in ("-f", "-F", "--raw-field", "--field") and index + 1 < len(argv):
            key, _, value = argv[index + 1].partition("=")
            result[key] = value
    return result


def body(argv):
    if "--body-file" in argv:
        return Path(option(argv, "--body-file")).read_text(encoding="utf-8")
    return option(argv, "--body", "-b")


def positional(argv, start):
    """The first argument after argv[start:] that is not an option or an option's value."""
    takes_value = {"--repo", "-R", "--json", "--jq", "-q", "--body", "-b", "--body-file", "--title", "-t", "--head",
                   "--base", "--state", "--limit", "-L", "--branch", "--label", "-l", "--add-label", "--name", "-n",
                   "--dir", "-D", "--method", "-X", "-f", "-F", "--raw-field", "--field", "--input", "-H", "--header"}
    skip = False
    for word in argv[start:]:
        if skip:
            skip = False
        elif word in takes_value:
            skip = True
        elif not word.startswith("-"):
            return word
    return None


def number_of(value):
    """A PR or issue number from a bare number or a URL ending in one."""
    if value is None:
        raise Unmapped()
    match = re.search(r"(\d+)/?$", value)
    if not match:
        raise Unmapped()
    return str(int(match.group(1)))


def select(value, argv):
    """Apply --json FIELD,... selection; anything else (such as --jq) is unmapped."""
    if "--jq" in argv or "-q" in argv:
        raise Unmapped()
    names = option(argv, "--json")
    if names is None:
        return value
    if isinstance(value, list):
        return [{name: item.get(name) for name in names.split(",")} for item in value]
    return {name: value.get(name) for name in names.split(",")}


# ---- views in gh's JSON shape ----------------------------------------------------

def issue_url(state, number):
    return f"{HOST}/{state['repo']}/issues/{number}"


def pr_url(state, number):
    return f"{HOST}/{state['repo']}/pull/{number}"


def issue_view(state, number, issue):
    return {"number": int(number), "title": issue["title"], "body": issue.get("body", ""), "url": issue_url(state, number),
            "state": issue.get("state", "OPEN").upper(), "labels": [{"name": name} for name in issue.get("labels", [])],
            "author": {"login": issue.get("author", state["viewer"]["login"])},
            "comments": [{"body": c["body"], "author": {"login": c["author"]}} for c in issue.get("comments", [])]}


def issue_rest(state, number, issue):
    return {"number": int(number), "title": issue["title"], "body": issue.get("body", ""),
            "html_url": issue_url(state, number), "state": issue.get("state", "open").lower(),
            "labels": [{"name": name} for name in issue.get("labels", [])],
            "user": {"login": issue.get("author", state["viewer"]["login"])}}


def pr_view(state, number, pull):
    status = "MERGED" if pull.get("merged") else pull.get("state", "open").upper()
    return {"number": int(number), "url": pr_url(state, number), "isDraft": pull.get("draft", True),
            "body": pull.get("body", ""), "title": pull.get("title", ""), "headRefName": pull["head"],
            "baseRefName": pull["base"], "state": status, "headRefOid": pull.get("head_sha"),
            "autoMergeRequest": {"enabledBy": {"login": state["viewer"]["login"]}} if pull.get("auto_merge") else None}


def run_view(run):
    return {"databaseId": run["id"], "workflowName": run.get("name", ""), "status": run.get("status", "completed"),
            "conclusion": run.get("conclusion"), "url": run.get("html_url", ""), "headSha": run.get("head_sha", ""),
            "headBranch": run.get("head_branch", ""), "attempt": run.get("run_attempt", 1)}


def advance(entry):
    """Return the current scripted value and move to the next; the last value sticks."""
    sequence = entry["sequence"]
    index = min(entry.get("read", 0), len(sequence) - 1)
    entry["read"] = index + 1
    return sequence[index]


# ---- gh commands ------------------------------------------------------------------

def repo_view(state, argv):
    if option(argv, "--jq", "-q") == ".nameWithOwner":
        return state["repo"]
    if "--jq" in argv or "-q" in argv:
        raise Unmapped()
    return json.dumps(select({"nameWithOwner": state["repo"]}, argv))


def new_number(state):
    number = str(state["next_number"])
    state["next_number"] += 1
    return number


def pr_list(state, argv):
    head, base, wanted = option(argv, "--head"), option(argv, "--base"), option(argv, "--state", default="open")
    rows = []
    for number, pull in state["pulls"].items():
        view = pr_view(state, number, pull)
        if head and pull["head"] != head or base and pull["base"] != base:
            continue
        if wanted != "all" and view["state"].lower() != wanted:
            continue
        rows.append(view)
    return json.dumps(select(rows, argv))


def find_pull(state, argv, start=2):
    number = number_of(positional(argv, start))
    if number not in state["pulls"]:
        raise Failed(f"no pull requests found for {number}")
    return number, state["pulls"][number]


def pr_view_command(state, argv):
    number, pull = find_pull(state, argv)
    return json.dumps(select(pr_view(state, number, pull), argv))


def pr_create(state, argv):
    number = new_number(state)
    state["pulls"][number] = {"head": option(argv, "--head"), "base": option(argv, "--base"), "title": option(argv, "--title", "-t"),
                              "body": body(argv), "draft": "--draft" in argv, "state": "open", "merged": False,
                              "auto_merge": False, "head_sha": None, "comments": [], "reviews": [], "review_comments": [],
                              "review_threads": []}
    return pr_url(state, number)


def pr_edit(state, argv):
    number, pull = find_pull(state, argv)
    text = body(argv)
    if text is None:
        raise Unmapped()
    pull["body"] = text
    return pr_url(state, number)


def pr_ready(state, argv):
    number, pull = find_pull(state, argv)
    pull["draft"] = "--undo" in argv
    return ""


def pr_merge(state, argv):
    number, pull = find_pull(state, argv)
    if "--disable-auto" in argv:
        pull["auto_merge"] = False
    elif "--auto" in argv:
        pull["auto_merge"] = True
    else:
        raise Unmapped()
    return ""


def find_issue(state, number):
    if number not in state["issues"]:
        raise Failed(f"Could not resolve to an issue with the number of {number}")
    return state["issues"][number]


def issue_view_command(state, argv):
    number = number_of(positional(argv, 2))
    return json.dumps(select(issue_view(state, number, find_issue(state, number)), argv))


def issue_create(state, argv):
    number = new_number(state)
    labels = [value for index, value in enumerate(argv) if index and argv[index - 1] in ("--label", "-l")]
    issue = {"title": option(argv, "--title", "-t"), "body": body(argv) or "", "state": "open", "labels": [],
             "author": state["viewer"]["login"], "comments": [], "events": []}
    state["issues"][number] = issue
    for label in labels:
        add_label(state, issue, label)
    return issue_url(state, number)


def add_label(state, issue, label):
    if label not in issue["labels"]:
        issue["labels"].append(label)
    issue.setdefault("events", []).append({"event": "labeled", "label": {"name": label}, "actor": dict(state["viewer"])})


def issue_comment(state, argv):
    number = number_of(positional(argv, 2))
    text = body(argv)
    if text is None:
        raise Unmapped()
    issue = find_issue(state, number)
    issue.setdefault("comments", []).append({"body": text, "author": state["viewer"]["login"]})
    return f"{issue_url(state, number)}#issuecomment-{len(issue['comments'])}"


def issue_edit(state, argv):
    number = number_of(positional(argv, 2))
    labels = [value for index, value in enumerate(argv) if index and argv[index - 1] == "--add-label"]
    if not labels or any(word in argv for word in ("--title", "--body", "--remove-label")):
        raise Unmapped()
    issue = find_issue(state, number)
    for value in labels:
        for label in value.split(","):
            add_label(state, issue, label)
    return issue_url(state, number)


def run_list(state, argv):
    branch = option(argv, "--branch", "-b")
    limit = int(option(argv, "--limit", "-L", default="20"))
    runs = [run_view(run) for run in state["actions"]["runs"] if not branch or run.get("head_branch") == branch]
    return json.dumps(select(runs[:limit], argv))


def run_view_command(state, argv):
    run_id = positional(argv, 2)
    if "--log-failed" not in argv:
        raise Unmapped()
    if run_id not in state["actions"]["logs"]:
        raise Failed(f"no failed log for run {run_id}")
    return state["actions"]["logs"][run_id]


def run_download(state, argv):
    """--name extracts into --dir; --pattern extracts each match into --dir/<artifact>, as gh does."""
    run_id, directory = positional(argv, 2), option(argv, "--dir", "-D")
    name, pattern = option(argv, "--name", "-n"), option(argv, "--pattern", "-p")
    if not directory or not (name or pattern):
        raise Unmapped()
    artifacts = state["actions"]["artifacts"].get(run_id, {})
    chosen = {name: ""} if name else {key: key for key in sorted(artifacts) if fnmatch.fnmatchcase(key, pattern)}
    if not chosen or any(key not in artifacts for key in chosen):
        raise Failed("no artifact matches any of the names or patterns provided")
    for key, folder in chosen.items():
        for filename, content in artifacts[key].items():
            target = Path(directory) / folder / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return ""


# ---- gh api -------------------------------------------------------------------------

def api(state, argv):
    words = argv[1:]
    endpoint = positional(argv, 1)
    if endpoint is None:
        raise Unmapped()
    values = fields(words)
    method = option(words, "--method", "-X", default="POST" if values and endpoint != "graphql" else "GET").upper()
    if endpoint == "graphql":
        return json.dumps(graphql(state, values))
    parts = urlsplit(endpoint)
    query = {key: value[0] for key, value in parse_qs(parts.query).items()}
    path = parts.path.strip("/")
    prefix = f"repos/{state['repo']}/"
    if not path.startswith(prefix):
        raise Unmapped()
    path = path[len(prefix):]
    for pattern, wanted, handler in ROUTES:
        match = re.fullmatch(pattern, path)
        if match and wanted == method:
            value = handler(state, *match.groups(), query=query, values=values)
            break
    else:
        raise Unmapped()
    if "--jq" in words or "-q" in words:
        raise Unmapped()
    if "--paginate" in words and "--slurp" in words:
        value = [value]
    return json.dumps(value)


def issue_or_pull(state, number):
    for key in ("issues", "pulls"):
        if number in state[key]:
            return state[key][number]
    raise Failed("Not Found (HTTP 404)")


def comment_rest(comment):
    return {"body": comment["body"], "user": {"login": comment["author"]}}


def api_issue_comments(state, number, **_):
    return [comment_rest(c) for c in issue_or_pull(state, number).get("comments", [])]


def api_pull_list(key):
    def handler(state, number, **_):
        if number not in state["pulls"]:
            raise Failed("Not Found (HTTP 404)")
        return state["pulls"][number].get(key, [])
    return handler


def api_issues(state, query, **_):
    wanted = query.get("state", "open")
    labels = [x for x in query.get("labels", "").split(",") if x]
    rows = []
    for number, issue in state["issues"].items():
        if wanted != "all" and issue.get("state", "open").lower() != wanted:
            continue
        if any(label not in issue.get("labels", []) for label in labels):
            continue
        rows.append(issue_rest(state, number, issue))
    return rows


def api_issue_events(state, number, **_):
    return find_issue(state, number).get("events", [])


def api_permission(state, login, **_):
    if login not in state["collaborators"]:
        raise Failed("Not Found (HTTP 404)")
    return {"permission": state["collaborators"][login], "user": {"login": login}}


def api_check_runs(state, sha, **_):
    rows = []
    for entry in state["checks"].get(sha, []):
        value = advance(entry)
        rows.append({"name": entry["name"], "head_sha": sha, "status": "in_progress" if value == "pending" else "completed",
                     "conclusion": None if value == "pending" else value})
    return {"total_count": len(rows), "check_runs": rows}


def api_status(state, sha, **_):
    rows = [{"context": entry["context"], "state": advance(entry)} for entry in state["statuses"].get(sha, [])]
    values = {row["state"] for row in rows}
    combined = ("failure" if values & {"failure", "error"} else "pending" if "pending" in values or not rows else "success")
    return {"sha": sha, "state": combined, "total_count": len(rows), "statuses": rows}


def api_post_status(state, sha, values, **_):
    if values.get("state") not in {"pending", "success", "failure", "error"} or not values.get("context"):
        raise Unmapped()
    entries = state["statuses"].setdefault(sha, [])
    entry = next((e for e in entries if e["context"] == values["context"]), None)
    if entry is None:
        entry = {"context": values["context"]}
        entries.append(entry)
    entry.update({"sequence": [values["state"]], "read": 0, "description": values.get("description", "")})
    return {"context": values["context"], "state": values["state"]}


def api_workflow_runs(state, workflow, query, **_):
    runs = [run for run in state["actions"]["runs"] if run.get("path", "").endswith("/" + workflow)]
    if query.get("branch"):
        runs = [run for run in runs if run.get("head_branch") == query["branch"]]
    runs = runs[:int(query.get("per_page", 30))]
    return {"total_count": len(runs), "workflow_runs": runs}


def api_jobs(state, run_id, **_):
    jobs = state["actions"]["jobs"].get(run_id, [])
    return {"total_count": len(jobs), "jobs": jobs}


ROUTES = [
    (r"issues/(\d+)/comments", "GET", api_issue_comments),
    (r"pulls/(\d+)/comments", "GET", api_pull_list("review_comments")),
    (r"pulls/(\d+)/reviews", "GET", api_pull_list("reviews")),
    (r"issues", "GET", api_issues),
    (r"issues/(\d+)/events", "GET", api_issue_events),
    (r"collaborators/([^/]+)/permission", "GET", api_permission),
    (r"commits/([0-9a-f]+)/check-runs", "GET", api_check_runs),
    (r"commits/([0-9a-f]+)/status", "GET", api_status),
    (r"statuses/([0-9a-f]+)", "POST", api_post_status),
    (r"actions/workflows/([^/]+)/runs", "GET", api_workflow_runs),
    (r"actions/runs/(\d+)/jobs", "GET", api_jobs),
]


def graphql(state, values):
    """The review-thread query integrations/github.py sends; all threads fit one page."""
    query = values.get("query", "")
    if "reviewThreads" not in query or "node(id:" in query:
        raise Unmapped()
    owner, name = state["repo"].split("/", 1)
    if (values.get("owner"), values.get("name")) != (owner, name):
        raise Failed("Could not resolve to a Repository")
    number = values.get("number", "")
    if number not in state["pulls"]:
        raise Failed("Could not resolve to a PullRequest")
    nodes = []
    for thread in state["pulls"][number].get("review_threads", []):
        comments = [{"id": c.get("id", ""), "body": c["body"], "url": c.get("url", ""), "author": {"login": c["author"]}}
                    for c in thread.get("comments", [])]
        nodes.append({"id": thread["id"], "isResolved": thread.get("resolved", False), "path": thread.get("path"),
                      "line": thread.get("line"),
                      "comments": {"nodes": comments, "pageInfo": {"hasNextPage": False, "endCursor": None}}})
    page = {"nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}
    return {"data": {"repository": {"pullRequest": {"reviewThreads": page}}}}


COMMANDS = [
    (("repo", "view"), repo_view),
    (("pr", "list"), pr_list),
    (("pr", "view"), pr_view_command),
    (("pr", "create"), pr_create),
    (("pr", "edit"), pr_edit),
    (("pr", "ready"), pr_ready),
    (("pr", "merge"), pr_merge),
    (("issue", "view"), issue_view_command),
    (("issue", "create"), issue_create),
    (("issue", "comment"), issue_comment),
    (("issue", "edit"), issue_edit),
    (("run", "list"), run_list),
    (("run", "view"), run_view_command),
    (("run", "download"), run_download),
    (("api",), api),
]


def main(argv):
    path = Path(os.environ["PLOVI_TEST_GITHUB_STATE"])
    state = dict(empty_state(), **(json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}))
    calls_path = path.with_suffix(".calls.json")
    calls = json.loads(calls_path.read_text(encoding="utf-8")) if calls_path.exists() else []
    try:
        text = body(argv)
    except (OSError, Unmapped):
        text = None
    calls.append({"argv": argv, "body": text})
    calls_path.write_text(json.dumps(calls), encoding="utf-8")
    handler = next((h for prefix, h in COMMANDS if tuple(argv[:len(prefix)]) == prefix), None)
    try:
        if handler is None:
            raise Unmapped()
        output = handler(state, argv)
    except Unmapped:
        print("unmapped gh call: " + json.dumps(argv), file=sys.stderr)
        return UNMAPPED
    except Failed as exc:
        print(f"gh: {exc}", file=sys.stderr)
        return 1
    path.write_text(json.dumps(state, indent=1), encoding="utf-8")
    if output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
