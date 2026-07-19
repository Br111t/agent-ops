# ADR 005: Use Run-Scoped Local SQLite Checkpoints

## Status

Accepted

## Context

The diagnostic run contract now provides stable UUID identity, ordered lifecycle
stages, and version provenance. The next persistence layer must retain graph state
across process restarts without requiring a hosted service or changing the target
repository.

LangGraph checkpointers organize state by `thread_id`. Introducing a second unrelated
identifier would make correlation and future resume behavior unnecessarily
ambiguous. SQLite connection lifetime and database placement also need explicit
ownership because checkpoints may contain repository paths and captured evidence.

## Decision

The synchronous CLI uses `langgraph-checkpoint-sqlite` and maps each diagnostic run
UUID directly to its LangGraph `thread_id`.

The CLI opens one SQLite connection, compiles the graph with its saver, invokes or
queries the graph, and closes the connection through a context manager. The default
database is `checkpoints.sqlite3` under `$AGENT_OPS_HOME` when configured, otherwise
under `~/.agent-ops`.

A custom checkpoint database must be outside the repository being inspected. On
POSIX systems the data directory is created for the current user and the database
file is restricted to user read/write access.

Checkpoint serialization explicitly allows only the Agent-Ops Pydantic models and
enums that can occur in graph state, in addition to LangGraph's built-in safe types.
The saver does not use the permissive unregistered-type fallback.

This increment persists completed state and super-step history but does not claim
safe resume. The new-run CLI rejects a run ID with existing checkpoint history until
resume semantics are implemented.

## Consequences

- Diagnostic state survives CLI and database-connection restarts.
- Run IDs, checkpoint threads, reports, and future API resources share one identity.
- Target repositories remain unchanged by default checkpointing.
- Existing checkpoint history is preserved instead of being silently replayed.
- Strict checkpoint deserialization remains compatible with the graph's structured
  state while rejecting unregistered application types.
- The SQLite saver adds local I/O and a small runtime dependency.
- The synchronous SQLite backend is suitable for the current local CLI, not a future
  high-concurrency service.
- Resume, history presentation, retention, time-travel forks, and side-effect replay
  controls remain separate Phase 2 increments.

## Alternatives Considered

### Store checkpoints inside each target repository

Rejected because the database would mutate the repository, contaminate its content
snapshot, and risk accidental source-control inclusion.

### Use a random LangGraph thread ID separate from the run UUID

Rejected because two identities would complicate correlation and resume without
providing a safety benefit.

### Use only in-memory checkpoints

Rejected because state would be lost when the CLI process exits and would not provide
the durability required by Phase 2.

### Introduce PostgreSQL immediately

Rejected because the current local synchronous workflow does not justify an external
service. PostgreSQL remains the likely boundary for a concurrent deployed API.
