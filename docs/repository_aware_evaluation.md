# Repository-Aware Evaluation Strategy

## Purpose

Evaluation is part of Agent-Ops itself, not a final demonstration step. The system
must measure whether its commands, classifications, evidence, recommendations, and
future corrections are reliable before increasing autonomy.

The first evaluation target is the implemented deterministic diagnostic pipeline:

```text
Repository profile
        -> framework detection
        -> approved execution evidence
        -> parsed and normalized evidence
        -> failure classification
```

Later evaluations may cover repository retrieval, generated explanations, candidate
patches, sandbox verification, multimodal evidence, and specialist agents.

## Evaluation Principles

1. **Trusted references are independent.** Do not generate a case's expected answer
   by calling the implementation being evaluated.
2. **Deterministic metrics come first.** Exact labels, schema checks, evidence
   validation, and safety rules are authoritative where they apply.
3. **Evidence quality is measured separately from outcome accuracy.** A correct label
   with invented reasoning is not a fully correct diagnostic result.
4. **Abstention is valid behavior.** `unknown`, `unparsed_failure`, and broad fallback
   categories should be rewarded when the evidence does not support specificity.
5. **Versions are reproducible.** Dataset, code, classifier, workflow, prompt, model,
   and evaluator versions are captured as applicable.
6. **Real evidence is sanitized.** Secrets, credentials, personal data, and private
   repository content must not enter a committed dataset.
7. **Evaluation does not mutate target repositories.** Evaluation fixtures use
   isolated repositories or structured captured evidence.

## Unit Tests and Evaluation Cases

Unit tests and evaluation cases have different purposes:

| Unit tests | Evaluation cases |
| --- | --- |
| Verify one contract or rule | Measure behavior across a representative corpus |
| Usually fail on one exact regression | Expose tradeoffs and category confusion |
| May mock surrounding components | Prefer realistic end-to-end evidence |
| Live with implementation tests | Carry dataset identity and provenance |

Existing classifier tests are useful seeds, but the evaluation dataset should also
contain realistic raw and normalized pytest evidence, ambiguous cases, partial
output, and combinations of competing markers.

## Dataset Design

The first dataset belongs under `evals/datasets/`. A Python fixture module is
acceptable for the initial small corpus. As the corpus grows, a versioned JSONL
format should be preferred so data can evolve independently of executable code
without adding a parsing dependency.

A classification case should contain at least:

```python
class ClassificationEvaluationCase(BaseModel):
    case_id: str
    dataset_version: str
    source_type: Literal["synthetic", "sanitized_real", "regression"]
    description: str
    framework_profile: TestFrameworkProfile
    normalized_evidence: NormalizedExecutionEvidence | None
    expected_category: FailureCategory
    expected_evidence_markers: tuple[str, ...] = ()
    forbidden_evidence_markers: tuple[str, ...] = ()
    expected_abstention: bool = False
    notes: str | None = None
```

If a future case begins with raw subprocess output, preserve that raw fixture and
evaluate parsing, normalization, and classification separately as well as together.

### Required initial coverage

The initial corpus should include:

- passed execution with and without a recognizable summary;
- timeout with complete and partial output;
- no tests collected;
- import and collection errors;
- fixture setup errors;
- assertion failures;
- browser and environment failures;
- test-data failures;
- application failures;
- broad test errors and test failures;
- unsupported frameworks;
- nonzero exits with malformed or unrecognized output;
- missing and conflicting evidence;
- Windows and POSIX traceback paths;
- duplicate evidence markers; and
- precedence cases containing markers from more than one category.

Reference cases should be labeled according to
[`failure-taxonomy.md`](failure-taxonomy.md).

## Initial Deterministic Metrics

### Classification metrics

- Overall exact category accuracy
- Per-category precision, recall, and F1
- Macro-averaged precision, recall, and F1
- Confusion matrix
- Broad-versus-specific classification accuracy
- Regression count relative to the baseline

Accuracy alone is insufficient because a common category can hide poor performance
on rare but important failures.

### Abstention and uncertainty metrics

- Correct abstention rate
- Unsupported-specificity rate
- Unknown and unparsed recall
- Missing-evidence reporting accuracy
- Confidence calibration when the corpus is large enough

Current confidence values express deterministic rule strength. They are not
calibrated probabilities.

### Evidence metrics

- Required evidence-marker coverage
- Forbidden or unsupported evidence rate
- Evidence duplication rate
- Evidence-reference validity when stable evidence identifiers are introduced
- Presence of explicit missing evidence where required

A future citation metric must verify that an evidence reference exists and supports
the associated claim. Checking only for the word `Source` or another citation marker
is not sufficient.

### Contract and safety metrics

- Pydantic and JSON schema validity
- Deterministic serialization and ordering
- Approved-command selection accuracy
- Unapproved-command attempt count
- Read-only inspection compliance
- Timeout and partial-output preservation
- Tool-selection accuracy when multiple tools become available

### Operational metrics

- End-to-end duration
- Per-stage duration
- Parser and classifier error rate
- Retry count
- Token usage and estimated cost when models are introduced
- Consistency across repeated nondeterministic runs

## Evaluation Runner

The initial runner belongs in `src/agent_ops/evaluation/evaluator.py`. It should:

1. Load and validate a named dataset version.
2. Execute a specified system version against every case.
3. Capture the actual classification and duration.
4. Calculate metrics without external API calls.
5. Return an immutable structured evaluation result.
6. Serialize a machine-readable report for baseline comparison.
7. Exit nonzero only when explicit evaluation gates fail.

`src/agent_ops/evaluation/metrics.py` should contain small, independently testable
metric functions. It should not know how subprocess execution or LangGraph routing
works.

The initial implementation should use the standard library and existing Pydantic
dependency. Pandas, DeepEval, and hosted evaluation platforms are not required for
deterministic classification metrics.

Run the current local classification dataset with:

```bash
python -m evals.run_failure_classification \
  --system-version <commit-sha-or-tree:sha> \
  --output evals/reports/<version>.json
```

The system version is required so a saved report is never labeled only as a mutable
working tree. Accepted baselines and CI candidates use a full commit SHA. Pre-commit
development candidates use the SHA returned by `git write-tree`, prefixed with
`tree:`. All intended files must be staged and `git diff --quiet` must succeed before
the run so the executing code matches that staged snapshot. Generated reports are
local artifacts and are not committed by default.

## Experiment Protocol

An experiment compares a baseline and candidate under the same controlled
conditions:

1. Select an immutable dataset version.
2. Record the baseline and candidate commit SHAs.
3. Record applicable workflow, classifier, prompt, model, and evaluator versions.
4. Run both versions against the same ordered cases.
5. Compare aggregate and per-case results.
6. Review regressions, improvements, abstentions, latency, and cost separately.
7. Preserve the complete report and environment metadata.

A candidate should not be selected merely because one aggregate score improves.
Safety, schema, evidence grounding, and important category regressions are blocking
dimensions.

Initial numerical thresholds should be established from a trustworthy baseline
rather than invented in advance. Once adopted, a threshold change requires an
explicit rationale.

Compare compatible reports with:

```bash
python -m evals.compare_failure_classification \
  evals/reports/<baseline>.json \
  evals/reports/<candidate>.json \
  --output evals/reports/<comparison>.json
```

Comparison requires matching dataset names, versions, case identifiers, and expected
categories. The default gate blocks any passing-to-failing case change or decline in
category accuracy, abstention accuracy, evidence accuracy, or macro F1. It records
latency changes without gating them. Invalid report schemas or incompatible datasets
are rejected before comparison.

## Future Repository Retrieval Evaluation

When Agent-Ops begins identifying relevant code, configuration, tests, fixtures,
logs, or symbols, cases should include trusted relevant-file and relevant-symbol
sets. Retrieval evaluation may then measure:

- precision at k;
- recall at k;
- mean reciprocal rank;
- nDCG;
- whether essential evidence was included in diagnostic context; and
- irrelevant-context volume.

Retrieval metrics evaluate selection quality. They do not by themselves establish
that a generated conclusion is correct.

## Future Generative Evaluation

When Agent-Ops generates explanations, recommendations, or candidate corrections,
evaluate at least:

- factual consistency with captured evidence;
- unsupported-claim frequency;
- recommendation relevance;
- evidence citation validity;
- completeness without unnecessary speculation;
- patch applicability and scope;
- focused-test recovery;
- regression-test outcomes; and
- human acceptance or rejection reasons.

### LLM-as-a-judge boundary

An LLM judge may supplement open-ended evaluation, but it must not replace exact
classification, schema, safety, or verification metrics. Judge criteria should be
scored separately rather than hidden in one composite score. Every judge run should
record the model, prompt or rubric version, input evidence, structured score, and
rationale. Ambiguous or high-impact disagreements require human adjudication.

The decision to establish deterministic evaluation first is recorded in
[`decisions/003-deterministic-evaluation-first.md`](decisions/003-deterministic-evaluation-first.md).

## Offline, Online, and UI Evaluation

The complete evaluation suite runs offline before a version is accepted. Expensive
LLM evaluation should not block every interactive diagnostic request. A deployed
system may sample completed traces for asynchronous monitoring after privacy and
cost controls are defined.

A future console may display saved metrics and trace links. Evaluation logic remains
in the backend and does not depend on Streamlit or another presentation layer.

## Observability Integrations

Agent-Ops should own a vendor-neutral trace and evaluation schema. Local output is
available by default. LangSmith may later be supported through an explicitly
configured exporter that redacts sensitive fields before transmission.

Agent-Ops must remain functional without a LangSmith account, API key, or network
connection.

## Initial Definition of Done

The deterministic evaluation baseline is complete when:

- evaluation case and result models are validated and immutable;
- every current failure category has positive and confusing-neighbor coverage;
- the dataset includes partial, malformed, and abstention cases;
- the runner emits overall, per-category, and per-case results;
- evidence and schema metrics are included;
- dataset and code versions are recorded;
- focused evaluation tests and the complete test suite pass;
- Ruff checks pass; and
- the baseline report is reproducible from documented commands.
