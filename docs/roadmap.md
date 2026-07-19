# Agent-Ops Roadmap

## Roadmap Principles

The roadmap advances Agent-Ops from a deterministic diagnostic foundation toward
reviewable correction workflows. Each phase must preserve evidence, command safety,
public output compatibility, and measurable evaluation.

Phases describe dependency order rather than calendar commitments. A capability is
complete only when its implementation, tests, structured output, and relevant
documentation are complete.

## Phase 0: Diagnostic Foundation

**Status:** Complete

Implemented foundations include:

- repository scanning;
- pytest detection;
- explicitly requested execution of approved test commands;
- process evidence capture and timeouts;
- pytest result parsing;
- local evidence extraction and normalization;
- deterministic failure classification; and
- single-workflow LangGraph orchestration;
- an immutable public diagnostic report that retains raw evidence;
- additive classification and normalized-evidence CLI output; and
- backward-compatible CLI serialization tests for every graph route.

## Phase 1: Evaluation Baseline

**Status:** Complete

**Goal:** Measure the diagnostic system before adding model-assisted analysis or
greater autonomy.

Deliverables:

- versioned failure-classification cases;
- evaluation case and result models;
- deterministic category, evidence, abstention, schema, safety, and latency metrics;
- per-category results and a confusion matrix;
- baseline and candidate experiment comparison;
- machine-readable evaluation reports; and
- documented dataset provenance and sanitization.

Implemented evaluation foundations include versioned classification cases,
immutable case and report models, category and evidence metrics, abstention checks,
latency capture, per-category results, a confusion matrix, and machine-readable JSON
output. Reports now require explicit system-version provenance and can be compared
case by case with deterministic no-regression gates suitable for CI. A separate
versioned command-safety corpus measures exact allowlist decisions without executing
candidate commands and blocks any incorrect approval or rejection. Dataset
governance now defines source provenance, raw-evidence boundaries, sanitization,
trusted labeling, semantic versioning, promotion gates, review checklists, and
incident handling. The checked-in Phase 1 corpora are explicitly recorded as
synthetic version `1.0.0` datasets.

LLM-as-a-judge evaluation is not required in this phase. The deterministic
evaluation decision is recorded in
[`decisions/003-deterministic-evaluation-first.md`](decisions/003-deterministic-evaluation-first.md).

## Phase 2: Durable Diagnostic Runs

**Status:** In progress

**Goal:** Resume long-running work without repeating completed diagnostic steps.

Deliverables:

- stable run identifiers;
- repository and version provenance;
- SQLite-backed graph checkpoints;
- explicit lifecycle and stage models;
- a controlled end-to-end demo-repository acceptance gate for durable runs;
- resume from the last safe checkpoint;
- retained checkpoint history for debugging;
- forked time-travel execution without deleting the original run; and
- replay protection for any side-effecting node.

Large execution artifacts remain in an evidence store and are referenced by
checkpoints rather than duplicated into graph state.

Implemented foundation:

- generated or caller-supplied UUID run identifiers;
- immutable running and completed lifecycle contracts with ordered stages and
  timezone-aware timestamps;
- Agent-Ops package version provenance;
- safe, non-executing reads of regular Git HEAD metadata; and
- deterministic SHA-256 snapshots of inspected non-ignored repository content,
  including local uncommitted changes;
- a local SQLite saver with deterministic connection lifetime;
- run UUIDs mapped directly to LangGraph thread IDs;
- checkpoint databases kept outside inspected repositories; and
- completed state and super-step history retained across graph reopen; and
- a synthetic pytest demo repository exercised through the real CLI, covering
  structured reports, Unicode execution evidence, SQLite history, and duplicate-run
  rejection without mocks.

Safe resume, user-facing history queries, time-travel forks, and complete replay
protection remain to be implemented. Until resume exists, the new-run CLI rejects
thread IDs with existing checkpoint history.

## Phase 3: Human-Reviewed Recommendations and Corrections

**Goal:** Turn diagnoses into reviewable, reversible candidate changes.

Deliverables:

- evidence-supported recommendations;
- relevant-file and symbol identification;
- candidate unified diffs;
- graph interrupts for explicit approval;
- isolated application of approved changes;
- focused and regression verification;
- comparison with the original baseline; and
- complete approval and tool history.

Agent-Ops does not automatically merge a verified change.

## Phase 4: Expanded Evidence and Repository Retrieval

**Goal:** Diagnose failures using more than pytest text output.

Candidate evidence sources:

- application and infrastructure logs;
- Playwright traces and screenshots;
- browser metadata;
- structured test reports;
- repository history and diffs; and
- relevant code, configuration, fixtures, and test data.

Retrieval quality will be measured with labeled relevant files and metrics such as
precision at k, recall at k, mean reciprocal rank, and nDCG. Multimodal conclusions
must retain references to the original artifacts.

## Phase 5: Streaming, Observability, and Console

**Goal:** Make long-running diagnostic work observable without exposing unrestricted
internal state.

Deliverables:

- structured run events;
- opt-in CLI streaming with a documented machine-readable format;
- local traces and aggregate performance metrics;
- optional redacted LangSmith export;
- checkpoint and approval status reporting; and
- a lightweight console prototype after the backend event contract stabilizes.

Token-level LLM streaming is a later user-experience enhancement. Factual stage
updates take priority.

## Phase 6: Model-Assisted Analysis and Optional Specialists

**Goal:** Add nondeterministic capabilities only where they improve measured results.

Candidate capabilities:

- model-assisted explanation and recommendation generation;
- LLM-as-a-judge evaluation for open-ended quality criteria;
- independent multimodal evidence analysis;
- parallel candidate-patch generation and verification; and
- optional specialist agents behind the coordinating workflow.

Transition to specialists requires evidence that parallel specialization improves
quality, latency, or coverage enough to justify routing, conflict resolution, cost,
and additional evaluation. The coordinator continues to own approvals and the final
diagnostic result.

## Cross-Phase Quality Gates

Every phase must preserve:

- explicitly approved commands only;
- read-only inspection by default;
- captured stdout, stderr, exit status, timeout state, and duration;
- evidence-supported conclusions and explicit uncertainty;
- deterministic and JSON-serializable public output;
- tests for success, failure, empty, partial, and malformed input;
- compatibility tests for public output changes;
- dataset and experiment version provenance; and
- documentation that separates implemented behavior from planned behavior.