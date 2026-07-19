"""Deterministic comparison and regression gates for evaluation reports."""

from collections.abc import Callable

from agent_ops.models import (
    ClassificationCaseComparison,
    ClassificationCaseEvaluationResult,
    ClassificationEvaluationComparison,
    ClassificationEvaluationReport,
    EvaluationCaseChange,
)

_GATED_METRICS: tuple[tuple[str, str, Callable[[ClassificationEvaluationReport], float]], ...] = (
    ("category accuracy", "category_accuracy_delta", lambda report: report.category_accuracy),
    (
        "abstention accuracy",
        "abstention_accuracy_delta",
        lambda report: report.abstention_accuracy,
    ),
    ("evidence accuracy", "evidence_accuracy_delta", lambda report: report.evidence_accuracy),
    ("macro F1", "macro_f1_delta", lambda report: report.macro_f1),
)


def compare_classification_reports(
    baseline: ClassificationEvaluationReport,
    candidate: ClassificationEvaluationReport,
) -> ClassificationEvaluationComparison:
    """Compare compatible reports and apply deterministic no-regression gates."""
    _validate_compatible_reports(baseline, candidate)

    candidate_cases = {case.case_id: case for case in candidate.cases}
    case_comparisons = tuple(
        _compare_case(baseline_case, candidate_cases[baseline_case.case_id])
        for baseline_case in baseline.cases
    )
    regressions = tuple(
        case.case_id for case in case_comparisons if case.change is EvaluationCaseChange.REGRESSION
    )
    gate_failures: list[str] = []

    if regressions:
        gate_failures.append(f"{len(regressions)} case regression(s): {', '.join(regressions)}")

    metric_deltas: dict[str, float] = {}
    for display_name, field_name, metric in _GATED_METRICS:
        delta = metric(candidate) - metric(baseline)
        metric_deltas[field_name] = delta

        if delta < 0.0:
            gate_failures.append(f"Candidate {display_name} decreased by {abs(delta):.6f}.")

    return ClassificationEvaluationComparison(
        dataset_name=baseline.dataset_name,
        dataset_version=baseline.dataset_version,
        baseline_system_version=baseline.system_version,
        candidate_system_version=candidate.system_version,
        total_cases=baseline.total_cases,
        passed_cases_delta=candidate.passed_cases - baseline.passed_cases,
        duration_seconds_delta=(candidate.duration_seconds - baseline.duration_seconds),
        cases=case_comparisons,
        gate_failures=tuple(gate_failures),
        **metric_deltas,
    )


def _validate_compatible_reports(
    baseline: ClassificationEvaluationReport,
    candidate: ClassificationEvaluationReport,
) -> None:
    """Require reports to describe the same immutable evaluation corpus."""
    if baseline.dataset_name != candidate.dataset_name:
        raise ValueError("Evaluation reports must use the same dataset name.")

    if baseline.dataset_version != candidate.dataset_version:
        raise ValueError("Evaluation reports must use the same dataset version.")

    baseline_cases = {case.case_id: case for case in baseline.cases}
    candidate_cases = {case.case_id: case for case in candidate.cases}

    if baseline_cases.keys() != candidate_cases.keys():
        raise ValueError("Evaluation reports must contain the same case IDs.")

    for case_id, baseline_case in baseline_cases.items():
        if baseline_case.expected_category is not candidate_cases[case_id].expected_category:
            raise ValueError(f"Expected category changed for evaluation case '{case_id}'.")


def _compare_case(
    baseline: ClassificationCaseEvaluationResult,
    candidate: ClassificationCaseEvaluationResult,
) -> ClassificationCaseComparison:
    """Compare pass state and classifications for one stable case identifier."""
    if baseline.passed and not candidate.passed:
        change = EvaluationCaseChange.REGRESSION
    elif not baseline.passed and candidate.passed:
        change = EvaluationCaseChange.IMPROVEMENT
    else:
        change = EvaluationCaseChange.UNCHANGED

    return ClassificationCaseComparison(
        case_id=baseline.case_id,
        expected_category=baseline.expected_category,
        baseline_actual_category=baseline.actual_category,
        candidate_actual_category=candidate.actual_category,
        baseline_passed=baseline.passed,
        candidate_passed=candidate.passed,
        change=change,
    )
