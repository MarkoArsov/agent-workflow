---
name: implement-tests
description: Author independent tests and obtain behavioral red evidence before product implementation.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# implement tests

1. Read the approved requirements and test contract. Locate existing fixtures and same-domain tests. Write tests for required behavior, boundary cases, and expected failures using the repository's established style.

2. In a runner stage, change only declared test_paths. Do not implement product behavior, commit, push, switch branches, or add unrelated test infrastructure.

3. Run the precise named checks. A meaningful red result identifies the expected test and an assertion against existing behavior. Import errors, syntax errors, missing dependencies, broken startup, and compilation errors are setup failures to repair before claiming red.

4. Keep assertions specific to the behavior rather than mirroring implementation details. Do not add sleeps, disable assertions, skip tests, or broaden fixtures to hide failures.

5. If a test cannot fail meaningfully before a new public interface exists, expose the gap in the plan and ask for the minimal interface decision. Do not claim a compiler error proves the feature is missing.

6. Report test identities, command results, affected paths, and genuine missing information. The runner executes the checks independently and freezes assertion-proven test files for implementation.

7. Return the runner's requested JSON status. In a direct invocation, explain the observed red evidence and the next implementation boundary.

