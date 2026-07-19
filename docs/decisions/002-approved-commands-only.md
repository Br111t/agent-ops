# ADR 002: Execute Approved Commands Only

- **Status:** Accepted
- **Date:** 2026-07-19

## Context

Agent-Ops inspects repositories and may execute their tests. Repository contents,
configuration, and test output are untrusted input. Allowing a model, repository
file, or user-provided string to construct arbitrary shell commands would create a
path to command injection, unintended mutation, credential exposure, and destructive
execution.

The default repository-inspection workflow does not require command execution.
Supported frameworks have a small set of known test commands that can be represented
as argument tuples and validated before execution.

## Decision

Agent-Ops will execute only commands selected by an explicit command policy for a
supported framework.

The execution boundary requires:

- an explicit user request such as `--run-tests`;
- a supported framework profile;
- a command tuple approved by policy;
- validation of the target repository path;
- direct subprocess execution without an interpolated shell string;
- a configured timeout; and
- complete capture of command, exit code, stdout, stderr, duration, and timeout state.

The default inspection path remains read-only and does not execute tests.

Repository files may inform framework detection, but they do not authorize arbitrary
commands. A script name found in a repository is not automatically an approved
execution strategy.

## Consequences

### Benefits

- Command injection and arbitrary shell access are constrained.
- Executions are reproducible and attributable to a known policy decision.
- Timeout, output, and failure evidence remain available for diagnosis.
- Unsupported frameworks fail safely without attempting guessed commands.

### Tradeoffs

- Repositories with custom test commands are unsupported until a reviewed policy is
  added.
- Framework detection and policy maintenance require explicit implementation and
  tests.
- Some valid repository workflows cannot be executed automatically.

## Future Mutations

Patch application, dependency installation, Git writes, deployment, and external
system actions are outside this test-command approval. Each requires a separate
policy and explicit human approval boundary.

Checkpoint replay does not grant new authority. A replayed side-effecting operation
must be idempotent or request approval again.

## Alternatives Considered

### Allow arbitrary shell commands with prompt instructions

Rejected because prompt instructions are not an enforceable security boundary.

### Trust commands declared by the target repository

Rejected because repository contents are untrusted and may execute unrelated or
destructive behavior.

### Never execute tests

Rejected because captured execution evidence is central to reliable diagnosis. The
approved-command boundary provides controlled capability without unrestricted shell
access.