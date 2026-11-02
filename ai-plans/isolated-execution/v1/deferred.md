# Deferred

No scheduler, egress allowlist proxy, plovi-in-container runtime, Windows container
path translation, hosted image publication, automatic image updates or toolchain
management. No remote push/PR, tracker comment/state change, deployment, real agent
installation or private credential migration is authorized by this specification.

macOS/Linux real-engine coverage is opt-in. Existing isolated host tests remain
mandatory across macOS/Linux/Windows. Account-authenticated inference is not a
planning readiness check. Cleanup uses recorded terminal lifecycle status; remote
PR synchronization is future work, not an implicit API action in clean.

No implementation or new product tests are written during specify. Planning checks
validate the contract and installed CLI capability only. Restricted fallback is
explicitly reported; an executed-container failure never triggers host rerun.
