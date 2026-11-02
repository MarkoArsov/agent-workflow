# Manual completion of issue #17

The user selected the implement skill to finish this task manually after the
retained pipeline escalated during implementation. Preserve its evidence and
leave the stopped run stopped; do not fabricate a completed pipeline record.
Continue on the existing task branch and allocation. No remote delivery is selected.

The fake missing-image test previously prepended Python before a future import,
so it failed before inspecting any image. The fake engine now records and rejects
the designated missing-image tag through its normal protocol, on every platform.
A regression proves that daemon probe and image inspect occur without a pull.
The simulation helper selects a supported preflight platform explicitly, while
production Windows rejection stays unchanged and separately tested. Echo in the
fake engine is portable without invoking a shell. Existing assertions are retained.
Both new protocol regressions failed before correction and pass afterward.
The protocol-health check is green-only because it exercises the implemented
wrapper, rather than pretending to be pre-implementation setup evidence.

Local requirements review also reproduced config opt-in mounting the user's home,
project, package or evidence directory. Reject these broad sources and their
ancestors; only a dedicated config directory is eligible. The new regression failed
for all four forbidden sources before the guard and passes afterward. No production
permission or factory-ownership bypass was introduced.

The opt-in real-engine smoke now checks mounted workspace reads, Git status/diff,
read-only mirror metadata, Linux UID mapping and actual container removal after
timeout. It still needs a local engine and prebuilt image; the default fake-engine
suite does not establish a real containment result.

The integrated service lease regression exercises a service and check through the
container wrapper, exports its endpoint, and observes task network creation and
owned container/network removal. It initially exposed an unparsed network-alias
flag in the fake engine; the fixture now recognizes that argument. The project
routing regression loads the repository's actual tracked profile/model settings
through the normal adapter under an isolated child home. It verifies both providers,
released legacy pins and honest retained-default output without a catalogue.

Final check results and review disposition are recorded after verification.

## Verification result

The final candidate passed 377 unittest cases with one approved skip: the opt-in
real-engine smoke. The Windows diagnostic runs on every host using its explicit
platform override. All 18 named contract checks passed across the full-suite,
focused and documentation runs. The portable evaluator reported seven provider-
subset contracts passed. Generated docs and native skill wrappers are current;
strict MkDocs and 4526 internal links/assets passed. The public-content/history
audit reported zero findings without a private denylist. Git whitespace checks pass.
These are local results, not claims about remote CI or a real engine.

Local requirements/diff review covered factory receipt validation, remote identity,
mirror ref protection, host delivery and terminal cleanup; container mount/env/
service/cleanup boundaries; evaluator stage isolation, provenance and frozen
snapshot compatibility; and the project-only dual-provider migration. The confirmed
mount-source defect was corrected and regression-tested before completion.

Independent Claude review remains pending explicit approval to transmit the source
diff and plans. Automatic approval review rejected that transmission in this manual
session; it was not retried or routed through another provider. No independent
review result is claimed. Implementation is ready for that review. The old stopped
pipeline evidence is preserved and has not been marked complete manually.
