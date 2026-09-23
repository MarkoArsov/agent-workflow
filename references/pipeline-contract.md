# Full plan contract

Use this reference when authoring a pipeline.json. Replace example repository IDs,
paths, model names, checks, and outcomes with confirmed project facts. Keep all four
plan files complete alongside the manifest.

~~~json
{
  "schema_version": 1,
  "task": "greeting",
  "plan_files": ["prompt.md", "requirements.md", "implementation.md", "deferred.md"],
  "repositories": [
    {
      "id": "app",
      "access": "write",
      "branch": "feature/greeting",
      "paths": ["src/**", "tests/**"],
      "test_paths": ["tests/**"]
    },
    {"id": "checks", "access": "read"}
  ],
  "stages": ["implement-tests", "implement", "review"],
  "checks": [
    {
      "id": "greeting-behavior",
      "repository": "app",
      "command": {
        "argv": ["python3", "-m", "unittest", "-v", "tests.test_greeting"],
        "cwd": ".",
        "timeout_seconds": 300
      },
      "parser": "unittest",
      "identities": ["test_greeting"],
      "phases": ["red", "green"]
    }
  ],
  "outcomes": [{"id": "greets-the-requested-name", "checks": ["greeting-behavior"]}],
  "limits": {
    "attempts_per_route": 2,
    "timeout_seconds": 1800,
    "inactivity_seconds": 300,
    "tool_timeout_seconds": 600
  },
  "references": [],
  "connectors": []
}
~~~

Routes inherit from the project or are explicitly selected in the plan. A stage
maps to an ordered array of provider/model objects; default is the fallback key
for an unspecified stage. A reasoning setting is optional.

Checks can name a repository command by string instead of repeating its object.
Generic checks need success_pattern and, for red evidence, failure_pattern.
Expected red test identities must appear as failed assertions. Commands that modify
source invalidate their own evidence.

Selecting commit-and-push requires delivery.commit_message and an explicit non-base
branch on every writable repository. Selecting draft-pr additionally requires
delivery.title and delivery.body_file, relative to the plan directory. This selects
only those actions, not reviewer requests or tracker updates.

Custom stage definitions come from the project's stages.json and are included by
ID in the ordered stage array. Check IDs refer to this plan's checks. Inputs are
exact repository-relative files; outputs may use declared path patterns.
