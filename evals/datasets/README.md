# Evaluation Datasets

This directory contains trusted, versioned inputs for deterministic Agent-Ops
evaluation. Dataset modules are executable reference data, not a place to store raw
logs or reports.

Before adding or changing a case, read
[`docs/evaluation-dataset-governance.md`](../../docs/evaluation-dataset-governance.md).

## Current datasets

- `failure_cases.py` defines the synthetic failure-classification corpus.
- `command_safety_cases.py` defines the synthetic command-policy corpus.

Both current datasets are version `1.0.0`. Generated reports belong under
`evals/reports/` and are ignored by default.

## Contribution rules

- Prefer synthetic evidence.
- Never commit raw workplace, customer, or private-repository evidence.
- Keep case identifiers stable and non-identifying.
- Assign expected results independently of the implementation under evaluation.
- Increment the dataset version for any behavioral or membership change.
- Promote cases only through a focused pull request using the governance checklist.

Use the
[`dataset-promotion.md`](../../.github/PULL_REQUEST_TEMPLATE/dataset-promotion.md)
pull-request template for a promotion change.
