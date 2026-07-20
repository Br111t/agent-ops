# ADR 006: Resume Only from Validated Safe Checkpoints

## Status

Accepted

## Context

SQLite checkpoints retain diagnostic graph state and the next scheduled operation
across process restarts. Continuing an arbitrary checkpoint can combine evidence
from different repository content, reuse the wrong run identity, or replay a
side-effecting operation such as test execution.

Phase 2 requires useful resume behavior before complete replay protection and
time-travel execution are available. The first resume boundary therefore needs to
continue deterministic work without claiming that every pending node is safe.

## Decision

The CLI exposes additive `--resume` behavior. Resume requires an explicit `--run-id`
and opens the checkpoint database using the requested repository as the existing
path-safety boundary. It loads the latest checkpoint and validates:

- checkpoint and persisted run identities match `--run-id`;
- the requested path matches the persisted target repository;
- the persisted run is incomplete and still running;
- the checkpoint has a pending graph operation;
- every pending operation is on the safe-resume allowlist; and
- when repository provenance has already been recorded, the current content
  snapshot matches the checkpoint snapshot.

After validation, the CLI invokes the graph with no new input so LangGraph continues
from the persisted next operation. The original execution intent, run identity,
timestamps, provenance, and completed node outputs remain in checkpoint state.

Repository inspection, framework detection, parsing, normalization,
classification, and completion are currently treated as non-side-effecting resume
operations. Test execution is explicitly excluded. A checkpoint whose next node is
`execute_tests` is rejected until that node has durable replay protection or renewed
approval semantics.

The new-run path continues to reject any existing checkpoint thread. Completed runs
cannot be resumed. `--run-tests` cannot be combined with `--resume` because resume
uses the original persisted execution intent rather than accepting replacement
input.

## Consequences

- Interrupted analysis can continue without repeating completed diagnostic steps.
- Repository changes cannot be silently combined with previously captured evidence.
- A resumed run preserves its original identity and lifecycle start time.
- Test execution cannot be accidentally replayed through the resume path.
- Some interrupted runs remain intentionally non-resumable until side-effect replay
  protection is implemented.
- User-facing history queries and time-travel forks remain separate Phase 2 work.

## Alternatives Considered

### Resume every pending node

Rejected because returning to a checkpoint does not reverse real-world effects and
test execution is not yet idempotent or protected by a durable execution ledger.

### Accept new graph input while resuming

Rejected because replacement repository paths or execution intent could make the
continued result inconsistent with its persisted provenance.

### Require a new run after every interruption

Rejected because it discards the primary benefit of retained graph checkpoints for
safe deterministic analysis stages.