"""GitHub CLI reads and explicitly selected delivery actions."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from ..util import WorkflowError, run

def slug(root, repo):
    configured = repo.get("github")
    if configured:
        return configured
    result = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], root)
    return result.stdout.strip()

def api(root, endpoint):
    result = run(["gh", "api", "--paginate", "--slurp", endpoint], root)
    pages = json.loads(result.stdout)
    return [item for page in pages for item in (page if isinstance(page, list) else [page])]

def comments(root, repo, number):
    target = slug(root, repo)
    result = {"issue_comments": api(root, f"repos/{target}/issues/{int(number)}/comments"),
              "review_comments": api(root, f"repos/{target}/pulls/{int(number)}/comments"),
              "reviews": api(root, f"repos/{target}/pulls/{int(number)}/reviews")}
    owner, name = target.split("/", 1)
    query = """query($owner:String!,$name:String!,$number:Int!,$cursor:String) {
      repository(owner:$owner,name:$name) { pullRequest(number:$number) {
        reviewThreads(first:100,after:$cursor) { nodes { id isResolved path line
          comments(first:100) { nodes { id body url author { login } } pageInfo { hasNextPage endCursor } }
        } pageInfo { hasNextPage endCursor } }
      } }
    }"""
    threads, cursor = [], None
    while True:
        argv = ["gh", "api", "graphql", "-f", f"query={query}", "-f", f"owner={owner}",
                "-f", f"name={name}", "-F", f"number={int(number)}"]
        if cursor:
            argv += ["-f", f"cursor={cursor}"]
        response = json.loads(run(argv, root).stdout)
        if response.get("errors"):
            raise WorkflowError("GitHub review thread retrieval failed")
        page = response["data"]["repository"]["pullRequest"]["reviewThreads"]
        for thread in page["nodes"]:
            inner = thread["comments"]
            while inner["pageInfo"]["hasNextPage"]:
                inner_query = """query($id:ID!,$cursor:String!) { node(id:$id) { ... on PullRequestReviewThread {
                  comments(first:100,after:$cursor) { nodes { id body url author { login } }
                  pageInfo { hasNextPage endCursor } } } } }"""
                extra = json.loads(run(["gh", "api", "graphql", "-f", f"query={inner_query}", "-f", f"id={thread['id']}",
                                        "-f", f"cursor={inner['pageInfo']['endCursor']}"], root).stdout)
                if extra.get("errors"):
                    raise WorkflowError("GitHub thread comment pagination failed")
                inner = extra["data"]["node"]["comments"]
                thread["comments"]["nodes"].extend(inner["nodes"])
            thread["comments"]["pageInfo"] = inner["pageInfo"]
        threads.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    result["threads"] = threads
    return result

def draft_pr(root, repo, branch, title, body):
    target = slug(root, repo)
    existing = json.loads(run(["gh", "pr", "list", "--repo", target, "--head", branch, "--base", repo["base_branch"],
                              "--state", "open", "--json", "url,isDraft"], root).stdout)
    if existing:
        if len(existing) != 1:
            raise WorkflowError("More than one matching PR; select it explicitly")
        return existing[0]["url"]
    with tempfile.TemporaryDirectory(prefix="workflow-pr-") as temporary:
        body_path = Path(temporary) / "body.md"; body_path.write_text(body)
        return run(["gh", "pr", "create", "--repo", target, "--head", branch, "--base", repo["base_branch"],
                    "--draft", "--title", title, "--body-file", body_path], root).stdout.strip()

def issue(root, repo, number):
    return json.loads(run(["gh", "issue", "view", str(int(number)), "--repo", slug(root, repo),
                           "--json", "title,body,url,labels,state"], root).stdout)

def checks(root, repo, branch):
    return json.loads(run(["gh", "run", "list", "--repo", slug(root, repo), "--branch", branch,
                           "--limit", "100", "--json", "databaseId,workflowName,status,conclusion,url,headSha"], root).stdout)

def failure_log(root, repo, run_id):
    return run(["gh", "run", "view", str(int(run_id)), "--repo", slug(root, repo), "--log-failed"], root).stdout

def bot_kind(login):
    name = login.lower().removesuffix("[bot]")
    if name in {"coderabbitai", "coderabbit"}:
        return "coderabbit"
    if name in {"cursor", "cursor-bugbot", "bugbot"}:
        return "bugbot"
    return None

def wait_bots(root, repo, number, *, rounds=3, interval=15, temporary_ready=False, authorized=False):
    import time
    if not 1 <= rounds <= 10 or not 1 <= interval <= 60:
        raise WorkflowError("Bot polling must be bounded")
    target = slug(root, repo)
    info = json.loads(run(["gh", "pr", "view", str(number), "--repo", target, "--json", "isDraft"], root).stdout)
    restore = temporary_ready and info["isDraft"]
    if restore and not authorized:
        raise WorkflowError("Temporary ready-for-review requires explicit action authorization")
    try:
        if restore:
            run(["gh", "pr", "ready", str(number), "--repo", target], root)
        for index in range(rounds):
            data = comments(root, repo, number)
            found = [x for key in ("issue_comments", "review_comments", "reviews")
                     for x in data[key] if bot_kind(x.get("user", {}).get("login", ""))]
            if found:
                return {"comments": found, "rounds": index + 1}
            if index + 1 < rounds:
                time.sleep(interval)
        return {"comments": [], "rounds": rounds, "status": "no bot feedback observed"}
    finally:
        if restore:
            run(["gh", "pr", "ready", str(number), "--repo", target, "--undo"], root)
