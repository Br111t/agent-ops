# ADR 004: Establish Stable Run and Repository Provenance Before Persistence

## Status

Accepted

## Context

Durable checkpoints require a stable identity for the diagnostic run and enough
version information to determine what code and target content a saved state
describes. A Git commit SHA alone is insufficient during local development because
the inspected repository may contain uncommitted changes. A content hash alone does
not identify the committed base or fit normal Git review workflows.

Agent-Ops also must not execute repository-controlled commands merely to collect
provenance.

## Decision

Each diagnostic graph creates or accepts a UUID before inspection and carries one
immutable `DiagnosticRun` through every successful stage. A public report is emitted
only after that run reaches the completed lifecycle state.

Run provenance records:

- the Agent-Ops package version;
- the resolved target repository path;
- an optional 40-character Git commit SHA read from bounded regular `.git` metadata;
  and
- a required SHA-256 snapshot of ordered non-ignored file paths and contents.

The Git revision identifies the committed base. The content snapshot identifies
what Agent-Ops actually inspected and therefore changes when included uncommitted
content changes. Git commands and repository code are not executed to derive either
identifier.

## Consequences

- A caller can correlate one diagnostic run across graph state, reports, and future
  checkpoints.
- Committed and uncommitted target states can be distinguished without requiring a
  clean working tree.
- Repeated snapshots add local I/O proportional to inspected repository content.
- Git worktrees and nonstandard Git metadata layouts may omit the optional revision
  until an explicit safe resolver is added; the content snapshot remains available.
- SQLite checkpointing can be added against a validated identity and lifecycle
  contract rather than defining those semantics inside the storage layer.

## Alternatives Considered

### Use only the target Git commit SHA

Rejected because it would label different uncommitted working trees as the same
target version.

### Run Git commands in the target repository

Rejected for this foundation because provenance collection must remain read-only
and must not cross the approved-command execution boundary.

### Introduce SQLite checkpoints first

Rejected because persisted state needs stable identity, lifecycle, and version
semantics before a storage schema can be treated as durable.
