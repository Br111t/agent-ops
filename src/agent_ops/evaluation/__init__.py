"""Evaluation capabilities for Agent-Ops diagnostic behavior."""

from agent_ops.evaluation.evaluator import (
    evaluate_failure_classification,
)
from agent_ops.evaluation.metrics import (
    calculate_category_metrics,
    calculate_confusion_matrix,
    calculate_evidence_coverage,
    calculate_macro_metrics,
    count_forbidden_evidence,
    is_abstention_category,
)

__all__ = [
    "calculate_category_metrics",
    "calculate_confusion_matrix",
    "calculate_evidence_coverage",
    "calculate_macro_metrics",
    "count_forbidden_evidence",
    "evaluate_failure_classification",
    "is_abstention_category",
]
