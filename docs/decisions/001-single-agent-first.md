# ADR 001: Use One Coordinating Agent First

- **Status:** Accepted
- **Date:** 2026-07-19

## Context

Agent-Ops has a sequential diagnostic responsibility: inspect a repository, detect
its test framework, execute an explicitly approved command when requested, preserve
evidence, classify the result, and report what the evidence supports.

The system may eventually analyze logs, code, screenshots, traces, and alternative
candidate patches in parallel. Introducing multiple independent agents now would
also introduce routing, shared-state ownership, duplicated context, conflict
resolution, additional cost, and a larger evaluation surface before those workloads
are independently valuable.

LangGraph nodes and deterministic modules already provide separation of concerns.
Parallel graph execution does not require multiple conversational agents.

## Decision

Agent-Ops will use one coordinating LangGraph workflow for the current diagnostic
and evaluation phases.

The coordinator:

- owns workflow routing and the final diagnostic state;
- invokes focused repository, tool, analysis, and evaluation modules;
- preserves evidence and provenance across stages;
- retains approval control for future side effects; and
- produces the final structured result.

Components return structured values and do not behave as independent agents unless
a later architectural decision explicitly promotes them.

## Consequences

### Benefits

- State ownership and approval boundaries remain clear.
- Deterministic functions are easy to test and evaluate independently.
- Evidence is less likely to be duplicated or contradicted across agents.
- The initial latency, token, and operational cost remain smaller.
- Checkpointing, streaming, and observability can be added to one coherent workflow.

### Tradeoffs

- One coordinator may become a throughput bottleneck for truly independent,
  expensive analysis.
- Specialist prompts and contexts cannot be optimized independently until a clear
  need exists.
- Parallel work must initially be expressed as graph nodes or ordinary concurrency.

## Reconsideration Triggers

This decision should be revisited when at least one of the following is supported by
evaluation evidence:

- logs, traces, screenshots, or code can be analyzed independently in parallel;
- several candidate patches can be generated and verified in isolated branches;
- specialist context substantially improves accuracy or coverage;
- the coordinating workflow becomes a demonstrated latency bottleneck; or
- independent verification produces meaningful reliability gains.

If specialists are introduced, the coordinator retains final report and approval
ownership. Specialists return structured findings, do not mutate shared state
directly, and receive independent evaluation coverage.

## Alternatives Considered

### Multiple agents from the beginning

Rejected because the current work is mostly sequential and deterministic. The added
coordination surface would not yet produce a measured capability gain.

### No graph orchestration

Rejected because explicit state transitions and conditional routing support future
checkpointing, human interrupts, time travel, and traceability without requiring
multiple agents.