# Full test-contract readiness revision

The user authorized fixing recurring automatic-workflow blocks. Reopen the existing
test-authoring stage once to audit and correct the entire authored #17 suite against
the approved F/C/E requirements before implementation. Reuse the existing test
bodies and cases; do not regenerate the suite or weaken required safety behavior.
This is a reviewed test-contract revision, not the assertion-preserving mechanical
repair path. Renew all setup and original red evidence before freezing again.

C2 requires factory-owned allocation metadata for contained execution. C4 requires
runtime/image probing and a pinned image ID before execution. Correct the successful
fake-runtime fixture to include legitimate temporary remote/allocation ownership;
make its fake runtime implement required probe/image responses. Assert that the
execution call uses run and --pull=never after preflight, instead of assuming the
first runtime invocation is execution. Add negative coverage for absent ownership
and invalid image metadata rather than making containment permissive.

Audit every remaining factory/container case for the same prerequisites, API
agreement, fake-tool protocol, image identity, mount/credential boundary, cleanup,
platform behavior and setup ordering. Exercise setup independently of absent product
APIs. Keep the evaluator requirements and cases; preserve original cases and all
valid assertions. Report each corrected assumption and its requirement mapping.
Do not implement factory/container/evaluator product code during test authoring.

The subsequent implementation must follow the corrected, fully checked contract.
The independent final review receives the requirements, revised tests and actual
product diff. Delivery permissions, native identities and checkout ownership stay
unchanged. Ordinary retry/resume retains bounded attempts; a reviewed contract
revision receives a fresh bounded fixture budget instead of inheriting old rounds.
