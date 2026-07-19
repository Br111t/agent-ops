# Diagnostic Demo Repository

This synthetic repository provides a small, deterministic pytest target for
Agent-Ops end-to-end acceptance tests. It is original test material maintained
with Agent-Ops and does not depend on network access or external services.

The suite exercises ordinary passing tests and Unicode output. Phase 2 acceptance
coverage runs the real Agent-Ops CLI against this repository, persists its graph
checkpoints to SQLite, and verifies that the same run ID cannot be replayed by the
new-run command.

The repository is intentionally kept reusable for safe-resume acceptance tests as
that Phase 2 capability is added.