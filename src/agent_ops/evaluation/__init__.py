"""Evaluation capabilities for Agent-Ops diagnostic behavior."""

from agent_ops.evaluation.comparison import (
    compare_classification_reports,
)
from agent_ops.evaluation.evaluator import (
    evaluate_command_safety,
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
from agent_ops.evaluation.reporting import (
    load_classification_report,
    write_evaluation_artifact,
)

__all__ = [
    "calculate_category_metrics",
    "calculate_confusion_matrix",
    "calculate_evidence_coverage",
    "calculate_macro_metrics",
    "compare_classification_reports",
    "count_forbidden_evidence",
    "evaluate_command_safety",
    "evaluate_failure_classification",
    "is_abstention_category",
    "load_classification_report",
    "write_evaluation_artifact",
]
