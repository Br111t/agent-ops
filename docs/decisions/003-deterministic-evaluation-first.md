# ADR 003: Establish Deterministic Evaluation Before LLM Judging

- **Status:** Accepted
- **Date:** 2026-07-19

## Context

Agent-Ops currently classifies structured pytest evidence with deterministic local
rules. Future versions may generate explanations, recommendations, relevant-file
selections, and candidate patches with language models.

LLM evaluation tools can assess open-ended qualities such as relevance and clarity,
but judges are nondeterministic, consume external resources, and may reproduce the
same unsupported assumptions as the system being evaluated. Exact categories,
schema validity, command safety, and verification outcomes can be measured directly.

## Decision

Agent-Ops will establish a versioned deterministic evaluation baseline before using
LLM-as-a-judge or increasing system autonomy.

The first evaluation harness will use trusted failure cases and code-based metrics
for:

- category accuracy and confusion;
- correct abstention;
- required and unsupported evidence;
- schema and serialization validity;
- command-policy compliance; and
- latency and regression comparison.

LLM judges may later supplement evaluation of generated explanations and
recommendations. They will not replace deterministic classification, safety,
evidence-reference, or test-verification metrics.

## Consequences

### Benefits

- Baselines are reproducible without an API key or network connection.
- Regressions can be attributed to specific cases and metrics.
- Safety and structured-output failures remain blocking regardless of prose quality.
- Later model-assisted features have a measurable comparison point.
- The runtime dependency set remains small.

### Tradeoffs

- Open-ended recommendation quality will not be fully measured in the first phase.
- Trusted dataset construction requires manual labeling and adjudication.
- Some semantic qualities need later human or model-assisted review.

## LLM Judge Requirements

When an LLM judge is introduced:

- score criteria separately rather than using one opaque composite score;
- require structured output;
- record judge model, rubric or prompt version, inputs, score, and rationale;
- preserve the evidence supplied to the judge;
- monitor judge consistency and cost; and
- require human adjudication for ambiguous or high-impact disagreements.

## Alternatives Considered

### Use an LLM judge for all evaluation immediately

Rejected because deterministic behavior should be measured directly and because a
judge cannot establish command safety or actual test recovery.

### Rely only on unit tests

Rejected because unit tests verify individual contracts but do not provide corpus
metrics, confusion analysis, version comparison, or dataset provenance.