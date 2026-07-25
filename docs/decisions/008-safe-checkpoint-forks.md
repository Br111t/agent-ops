# ADR 008: Fork Historical Checkpoints into New Runs

## Status

Accepted

## Context

Retained LangGraph history makes earlier diagnostic states available after a run has
continued or completed. Reusing one of those checkpoints in its original thread
would make the latest state ambiguous, mix conclusions from different paths, and
obscure which evidence belongs to which execution.

Returning to an earlier checkpoint also does not reverse side effects that already
occurred. In particular, a selected checkpoint before `execute_tests` can cause the
approved test command to run again.

## Decision

The CLI exposes additive `--fork` behavior. A fork requires:

- the source `--run-id`;
- an exact `--checkpoint-id`;
- the original repository path and checkpoint database; and
- a distinct `--fork-run-id`, generated when the caller does not supply one.

Agent-Ops loads the exact source snapshot and validates its thread and checkpoint
identity, repository path, content snapshot when available, lifecycle, required
state, and pending operation. The checkpoint must contain an initialized, running
diagnostic lifecycle with a supported continuation. Its lifecycle stage must match
the graph node that produced the pending operation.

After validation, Agent-Ops copies the selected state into a new LangGraph thread
whose thread ID equals the fork run UUID. It replaces the persisted run identity
with a new running `DiagnosticRun` and records immutable `source_run_id` and
`source_checkpoint_id` lineage. The source checkpoint thread is never updated or
deleted.

Forks do not accept arbitrary state or configuration edits. They continue from the
selected checkpoint's existing pending operation. If that continuation can reach
`execute_tests`, the invocation must supply `--approve-test-replay`. The permission
remains invocation-scoped and the execution node enforces it independently.

## Consequences

- Historical analysis can continue along a new path without changing the original
  run or its evidence.
- The fork receives an independent run ID, lifecycle timestamps, checkpoint history,
  and final diagnostic report.
- Reports and checkpoint-history summaries expose the exact source run and
  checkpoint.
- Fork creation fails if the target run ID already has checkpoint history.
- Input-only checkpoints, terminal checkpoints, malformed state, changed
  repositories, unsupported pending operations, and inconsistent lifecycle/node
  combinations cannot create a fork.
- A checkpoint after test execution can reuse captured evidence without rerunning
  tests.
- A checkpoint before test execution requires renewed approval and may repeat
  external side effects; the fork does not undo earlier effects.

## Alternatives Considered

### Branch inside the original checkpoint thread

Rejected because one thread would then represent multiple diagnostic run outcomes
and make the latest run state and public identity ambiguous.

### Copy the checkpoint and preserve the original run ID

Rejected because the copied history would no longer agree with the new LangGraph
thread identity.

### Permit state edits while forking

Rejected for this phase because an editable fork needs a separate validated schema,
provenance for every change, and additional approval boundaries.

### Treat original test approval as durable

Rejected because a fork is a new invocation and may replay side effects long after
the source run.
