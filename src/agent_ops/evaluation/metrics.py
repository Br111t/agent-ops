"""Deterministic metrics for Agent-Ops evaluation reports."""

from collections import Counter
from collections.abc import Sequence

from agent_ops.models import CategoryEvaluationMetrics, FailureCategory

_ABSTENTION_CATEGORIES = frozenset(
    {
        FailureCategory.TEST_ERROR,
        FailureCategory.TEST_FAILURE,
        FailureCategory.UNPARSED_FAILURE,
        FailureCategory.UNKNOWN,
    }
)


def calculate_category_metrics(
    expected: Sequence[FailureCategory],
    actual: Sequence[FailureCategory],
) -> tuple[CategoryEvaluationMetrics, ...]:
    """Calculate per-category precision, recall, and F1."""
    _validate_paired_categories(expected, actual)
    observed = set(expected) | set(actual)
    metrics: list[CategoryEvaluationMetrics] = []

    for category in FailureCategory:
        if category not in observed:
            continue

        true_positives = sum(
            expected_category is category and actual_category is category
            for expected_category, actual_category in zip(
                expected,
                actual,
                strict=True,
            )
        )
        false_positives = sum(
            expected_category is not category and actual_category is category
            for expected_category, actual_category in zip(
                expected,
                actual,
                strict=True,
            )
        )
        false_negatives = sum(
            expected_category is category and actual_category is not category
            for expected_category, actual_category in zip(
                expected,
                actual,
                strict=True,
            )
        )
        support = sum(category_value is category for category_value in expected)
        precision = _safe_ratio(
            true_positives,
            true_positives + false_positives,
        )
        recall = _safe_ratio(
            true_positives,
            true_positives + false_negatives,
        )
        f1 = _safe_ratio(
            2 * precision * recall,
            precision + recall,
        )

        metrics.append(
            CategoryEvaluationMetrics(
                category=category,
                support=support,
                true_positives=true_positives,
                false_positives=false_positives,
                false_negatives=false_negatives,
                precision=precision,
                recall=recall,
                f1=f1,
            )
        )

    return tuple(metrics)


def calculate_confusion_matrix(
    expected: Sequence[FailureCategory],
    actual: Sequence[FailureCategory],
) -> dict[str, dict[str, int]]:
    """Return an observed expected-by-actual confusion matrix."""
    _validate_paired_categories(expected, actual)
    observed = set(expected) | set(actual)
    categories = tuple(
        category
        for category in FailureCategory
        if category in observed
    )
    counts = Counter(zip(expected, actual, strict=True))

    return {
        expected_category.value: {
            actual_category.value: counts[
                (expected_category, actual_category)
            ]
            for actual_category in categories
        }
        for expected_category in categories
    }


def calculate_macro_metrics(
    categories: Sequence[CategoryEvaluationMetrics],
) -> tuple[float, float, float]:
    """Return macro precision, recall, and F1."""
    if not categories:
        return 0.0, 0.0, 0.0

    count = len(categories)

    return (
        sum(metric.precision for metric in categories) / count,
        sum(metric.recall for metric in categories) / count,
        sum(metric.f1 for metric in categories) / count,
    )


def calculate_evidence_coverage(
    evidence: Sequence[str],
    required_markers: Sequence[str],
) -> float:
    """Return the share of required markers found in evidence."""
    if not required_markers:
        return 1.0

    normalized_evidence = tuple(item.casefold() for item in evidence)
    matched = sum(
        any(
            marker.casefold() in evidence_item
            for evidence_item in normalized_evidence
        )
        for marker in required_markers
    )

    return matched / len(required_markers)


def count_forbidden_evidence(
    evidence: Sequence[str],
    forbidden_markers: Sequence[str],
) -> int:
    """Count forbidden markers present in classification evidence."""
    normalized_evidence = tuple(item.casefold() for item in evidence)

    return sum(
        any(
            marker.casefold() in evidence_item
            for evidence_item in normalized_evidence
        )
        for marker in forbidden_markers
    )


def is_abstention_category(category: FailureCategory) -> bool:
    """Return whether a category intentionally avoids a specific cause."""
    return category in _ABSTENTION_CATEGORIES


def _validate_paired_categories(
    expected: Sequence[FailureCategory],
    actual: Sequence[FailureCategory],
) -> None:
    """Require non-empty sequences with matching lengths."""
    if not expected:
        raise ValueError("At least one expected category is required.")

    if len(expected) != len(actual):
        raise ValueError("Expected and actual categories must have equal lengths.")


def _safe_ratio(numerator: float, denominator: float) -> float:
    """Return a ratio or zero when the denominator is zero."""
    if denominator == 0:
        return 0.0

    return numerator / denominator