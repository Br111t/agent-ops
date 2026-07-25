# ADR 007: Require Renewed Approval for Test Replay

## Status

Accepted

## Context

LangGraph checkpoints preserve graph state, including the original `run_tests`
intent. That persisted value records what the user requested when the diagnostic
run began, but it cannot safely authorize a later invocation. Resuming from
`initialize_run`, `inspect_repository`, `detect_framework`, or `execute_tests` can
reach approved test execution again.

Test commands are constrained by the command policy, but tests may still mutate
files, databases, or external systems. They are therefore not assumed to be
idempotent.

## Decision

The diagnostic graph uses immutable runtime context to carry test-execution
approval for exactly one invocation. The context is not checkpoint state and does
not survive a process restart.

The `execute_tests` node fails closed unless the current invocation carries test
approval. A new run receives that approval only from explicit `--run-tests`.

Resume validation examines both the immediate pending nodes and predecessor nodes
that can route to test execution. When resumed work may reach `execute_tests`, the
CLI requires `--approve-test-replay`. That flag supplies fresh approval to the
runtime context for the resumed invocation. Checkpoints that can only continue
through deterministic analysis do not require it.

The repository path, content snapshot, run identity, lifecycle, required state, and
supported pending-node checks remain mandatory regardless of approval.

## Consequences

- Persisted `run_tests` intent cannot silently authorize later test execution.
- Direct node execution and CLI resume share the same fail-closed runtime guard.
- Approval expires after one invocation and must be renewed for another replay.
- Resume from a checkpoint after test execution continues analysis without a new
  approval because it does not rerun tests.
- Time-travel forks can reuse this same approval boundary.
- Agent-Ops still does not claim that target-repository tests are idempotent.

## Alternatives Considered

### Treat the original `--run-tests` flag as durable approval

Rejected because checkpoint replay occurs in a new invocation and may repeat
external side effects long after the initial command.

### Assume approved test commands are idempotent

Rejected because command approval constrains which command may run; it does not
control the behavior of the target repository's tests.

### Guard only when `execute_tests` is the immediate next node

Rejected because earlier pending nodes can route to test execution and bypass an
immediate-node-only check.
