"""Evaluation runner for deterministic failure classification."""

from time import perf_counter

from agent_ops.analysis import classify_failure
from agent_ops.evaluation.metrics import (
    calculate_category_metrics,
    calculate_confusion_matrix,
    calculate_evidence_coverage,
    calculate_macro_metrics,
    count_forbidden_evidence,
    is_abstention_category,
)
from agent_ops.models import (
    ClassificationCaseEvaluationResult,
    ClassificationEvaluationDataset,
    ClassificationEvaluationReport,
    CommandSafetyCaseEvaluationResult,
    CommandSafetyEvaluationDataset,
    CommandSafetyEvaluationReport,
)
from agent_ops.safety import is_test_command_approved


def evaluate_failure_classification(
    dataset: ClassificationEvaluationDataset,
    *,
    system_version: str,
) -> ClassificationEvaluationReport:
    """Evaluate the deterministic classifier against a trusted dataset."""
    evaluation_started = perf_counter()
    case_results: list[ClassificationCaseEvaluationResult] = []

    for case in dataset.cases:
        case_started = perf_counter()
        classification = classify_failure(
            case.framework_profile,
            case.normalized_evidence,
        )
        duration_seconds = perf_counter() - case_started
        actual_abstention = is_abstention_category(classification.category)
        evidence_coverage = calculate_evidence_coverage(
            classification.evidence,
            case.required_evidence_markers,
        )
        unsupported_evidence_count = count_forbidden_evidence(
            classification.evidence,
            case.forbidden_evidence_markers,
        )
        category_correct = classification.category is case.expected_category
        abstention_correct = actual_abstention is case.expected_abstention
        evidence_correct = evidence_coverage == 1.0 and unsupported_evidence_count == 0

        case_results.append(
            ClassificationCaseEvaluationResult(
                case_id=case.case_id,
                expected_category=case.expected_category,
                actual_category=classification.category,
                category_correct=category_correct,
                expected_abstention=case.expected_abstention,
                actual_abstention=actual_abstention,
                abstention_correct=abstention_correct,
                evidence_coverage=evidence_coverage,
                unsupported_evidence_count=(unsupported_evidence_count),
                evidence_correct=evidence_correct,
                confidence=classification.confidence,
                duration_seconds=duration_seconds,
                passed=(category_correct and abstention_correct and evidence_correct),
            )
        )

    expected = tuple(case.expected_category for case in dataset.cases)
    actual = tuple(result.actual_category for result in case_results)
    category_metrics = calculate_category_metrics(
        expected,
        actual,
    )
    macro_precision, macro_recall, macro_f1 = calculate_macro_metrics(category_metrics)
    total_cases = len(case_results)

    return ClassificationEvaluationReport(
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        system_version=system_version,
        total_cases=total_cases,
        passed_cases=sum(result.passed for result in case_results),
        category_accuracy=(sum(result.category_correct for result in case_results) / total_cases),
        abstention_accuracy=(
            sum(result.abstention_correct for result in case_results) / total_cases
        ),
        evidence_accuracy=(sum(result.evidence_correct for result in case_results) / total_cases),
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        macro_f1=macro_f1,
        duration_seconds=perf_counter() - evaluation_started,
        confusion_matrix=calculate_confusion_matrix(
            expected,
            actual,
        ),
        categories=category_metrics,
        cases=tuple(case_results),
    )


def evaluate_command_safety(
    dataset: CommandSafetyEvaluationDataset,
    *,
    system_version: str,
) -> CommandSafetyEvaluationReport:
    """Evaluate the deterministic command policy without executing any command."""
    evaluation_started = perf_counter()
    case_results: list[CommandSafetyCaseEvaluationResult] = []

    for case in dataset.cases:
        case_started = perf_counter()
        actual_approved = is_test_command_approved(case.framework, case.command)
        duration_seconds = perf_counter() - case_started

        case_results.append(
            CommandSafetyCaseEvaluationResult(
                case_id=case.case_id,
                expected_approved=case.expected_approved,
                actual_approved=actual_approved,
                duration_seconds=duration_seconds,
                passed=actual_approved is case.expected_approved,
            )
        )

    total_cases = len(case_results)
    passed_cases = sum(result.passed for result in case_results)

    return CommandSafetyEvaluationReport(
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        system_version=system_version,
        total_cases=total_cases,
        passed_cases=passed_cases,
        approval_accuracy=passed_cases / total_cases,
        unsafe_approval_count=sum(
            not result.expected_approved and result.actual_approved for result in case_results
        ),
        safe_rejection_count=sum(
            result.expected_approved and not result.actual_approved for result in case_results
        ),
        duration_seconds=perf_counter() - evaluation_started,
        cases=tuple(case_results),
    )
