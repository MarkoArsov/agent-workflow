"""Plan hashes, proposals, approvals and the background-worker gate."""
from __future__ import annotations
from pathlib import Path
from .. import ledger, manifest as contracts, state
from ..util import WorkflowError, file_hash, read_json
from . import record, task_subject


def approved(project, task, sha):
    return any(e["type"] == "plan.approved" and e["data"].get("plan_sha256") == sha
               for e in ledger.events(project, subject=task_subject(task)))


def self_approve(project, plan, args, command):
    """Explicit launches approve the plan they start, once per plan hash."""
    from . import suppressed
    if suppressed():
        return None
    sha = contracts.plan_sha256(plan)
    if approved(project, plan["task"], sha):
        return None
    return record(project, task_subject(plan["task"]), "plan.approved",
                  {"plan_sha256": sha, "auto": True, "manifest": str(plan.get("_path", ""))}, args=args, command=command)


def propose(project, plan, args):
    """validate-plan records one plan.proposed per task and plan hash."""
    sha = contracts.plan_sha256(plan)
    if any(e["type"] == "plan.proposed" and e["data"].get("plan_sha256") == sha
           for e in ledger.events(project, subject=task_subject(plan["task"]))):
        return None
    return record(project, task_subject(plan["task"]), "plan.proposed",
                  {"plan_sha256": sha, "manifest": str(plan.get("_path", ""))}, args=args, command="validate-plan")


def require(project, manifest, saved):
    """Background workers start or continue only a plan whose current hash is approved."""
    sha = contracts.plan_sha256(manifest)
    if saved and saved.get("binding_sha256") and "plan_sha256" not in saved:
        return sha  # Runs that started before plan approvals existed are grandfathered.
    if saved and saved.get("plan_sha256") == sha:
        return sha
    if approved(project, manifest["task"], sha):
        return sha
    task = manifest["task"]
    raise WorkflowError(f"The plan for {task} has no recorded approval for its current contents, so the background "
                        f"worker did not start. Review the plan, then run plovi approve {task} --plan.")


def worker_gate(project, manifest):
    from .. import policy
    return bool(policy.effective(project, manifest)["values"]["execution"]["require_plan_approval"])


def locate(project, task, manifest_path=None):
    """Find a task's manifest: --manifest, the task-start receipt, then the saved run."""
    candidates = []
    if manifest_path:
        candidates.append(Path(manifest_path))
    else:
        from ..tasks import receipt_path
        receipt = read_json(receipt_path(project, task))
        if receipt is None:
            from ..factory import receipt_path as factory_receipt
            try:
                receipt = read_json(factory_receipt(project, task))
            except WorkflowError:
                receipt = None
        for row in (receipt or {}).get("repositories", []):
            if row.get("path"):
                candidates.append(Path(row["path"]) / project.profile["planning"]["directory"] / task / "pipeline.json")
        saved = read_json(state.directory(project, task) / "state.json", {})
        if saved.get("manifest_path"):
            candidates.append(Path(saved["manifest_path"]))
    for path in candidates:
        if path.is_file():
            plan = contracts.load(path, project)
            if plan["task"] != task:
                raise WorkflowError(f"{path} belongs to task {plan['task']}, not {task}. Pass the manifest for {task}.")
            return plan
    raise WorkflowError(f"plovi could not find the plan for {task}. Pass --manifest PATH.")


def describe(project, plan):
    sha = contracts.plan_sha256(plan)
    directory = Path(plan["_directory"])
    files = [{"path": name, "sha256": file_hash(directory / name)} for name in plan["plan_files"]]
    return {"operation": "approve", "kind": "plan", "task": plan["task"], "plan_sha256": sha, "digest": sha,
            "manifest": plan["_path"], "plan_files": files, "approved": approved(project, plan["task"], sha),
            "next": f"plovi approve {plan['task']} --plan --approve {sha}"}
