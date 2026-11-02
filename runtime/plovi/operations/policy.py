"""Project policy: show, and change by preview and digest."""
from __future__ import annotations
import sys
from .. import policy as project_policy
from ..util import WorkflowError
from . import preview_digest, record, register
from .tasks import project_for


@register("policy.show", "Show the effective project policy and where each value comes from", "plovi policy show [--json]",
          arguments={"json": {"type": "boolean"}}, mutates=False, risk="none")
def show(args):
    return project_policy.effective(project_for(args))


def _preview(args):
    project = project_for(args)
    edit = project_policy.plan_edit(project, args["key"], args["value"])
    preview = {"operation": "policy.set", "key": args["key"], "value": args["value"], "changed": edit["changed"],
               "before_sha256": edit["before_sha256"], "diff": edit["diff"]}
    preview["digest"] = preview_digest(preview)
    preview["next"] = f"plovi policy set {args['key']} {args['value']} --approve {preview['digest']}"
    return project, edit, preview


@register("policy.set", "Change one project policy value in plovi.toml", "plovi policy set KEY VALUE [--approve DIGEST | --yes] [--reason TEXT]",
          arguments={"key": {"type": "string", "description": "section.key"}, "value": {"type": "string", "description": "TOML value"},
                     "approve": {"type": "string", "description": "Digest from the preview"},
                     "yes": {"type": "boolean", "description": "Person shortcut; refused for agents"}},
          required=("key", "value"), mutates=True, risk="high", preview=lambda args: _preview(args)[2])
def set_value(args):
    agent = bool(args.get("actor_agent"))
    if agent and args.get("yes"):
        raise WorkflowError("Agents cannot use --yes. Show the preview to the person, then pass --approve DIGEST.")
    if not agent and not args.get("approve"):
        # A person's existing review flow: print the diff, then --yes or an interactive y.
        project = project_for(args)
        edit = project_policy.plan_edit(project, args["key"], args["value"])
        result = project_policy.set_value(project, args["key"], args["value"], yes=bool(args.get("yes")))
        if result.get("changed"):
            record(project, {"kind": "policy", "id": project.profile["project"]["id"]}, "policy.changed",
                   {"diff": edit["diff"]}, args=args, command="policy.set")
        return result
    project, edit, preview = _preview(args)
    if not args.get("approve"):
        return preview
    if args["approve"] != preview["digest"]:
        raise WorkflowError("The digest does not match this policy change; plovi.toml changed or the digest is wrong. "
                            "Run the preview again and approve its digest.")
    if not edit["changed"]:
        return {"changed": False, "key": args["key"]}
    project_policy.write_edit(project, edit)
    record(project, {"kind": "policy", "id": project.profile["project"]["id"]}, "policy.changed",
           {"diff": edit["diff"]}, args=args, command="policy.set")
    return {"changed": True, "key": args["key"], "diff": edit["diff"]}
