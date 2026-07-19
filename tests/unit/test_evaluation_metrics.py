"""Tests for deterministic evaluation metrics."""

import pytest

from agent_ops.evaluation import (
    calculate_category_metrics,
    calculate_confusion_matrix,
    calculate_evidence_coverage,
    calculate_macro_metrics,
    count_forbidden_evidence,
    is_abstention_category,
)
from agent_ops.models import FailureCategory


def test_category_metrics_are_perfect_for_matching_predictions() -> None:
    """Matching predictions should produce perfect observed metrics."""
    expected = (
        FailureCategory.PASSED,
        FailureCategory.TIMEOUT,
    )

    metrics = calculate_category_metrics(expected, expected)
    macro_metrics = calculate_macro_metrics(metrics)

    assert all(metric.precision == 1.0 for metric in metrics)
    assert all(metric.recall == 1.0 for metric in metrics)
    assert all(metric.f1 == 1.0 for metric in metrics)
    assert macro_metrics == (1.0, 1.0, 1.0)


def test_category_metrics_expose_false_positive_and_negative() -> None:
    """A confused prediction should affect both represented categories."""
    expected = (
        FailureCategory.PASSED,
        FailureCategory.TIMEOUT,
    )
    actual = (
        FailureCategory.PASSED,
        FailureCategory.PASSED,
    )

    metrics = {metric.category: metric for metric in calculate_category_metrics(expected, actual)}

    assert metrics[FailureCategory.PASSED].precision == 0.5
    assert metrics[FailureCategory.PASSED].recall == 1.0
    assert metrics[FailureCategory.TIMEOUT].precision == 0.0
    assert metrics[FailureCategory.TIMEOUT].recall == 0.0


def test_confusion_matrix_uses_stable_category_values() -> None:
    """The confusion matrix should count expected-by-actual outcomes."""
    expected = (
        FailureCategory.PASSED,
        FailureCategory.TIMEOUT,
    )
    actual = (
        FailureCategory.PASSED,
        FailureCategory.PASSED,
    )

    result = calculate_confusion_matrix(expected, actual)

    assert result["passed"]["passed"] == 1
    assert result["timeout"]["passed"] == 1
    assert result["timeout"]["timeout"] == 0


def test_evidence_metrics_match_case_insensitively() -> None:
    """Evidence markers should not depend on capitalization."""
    evidence = (
        "Import exception detected: ModuleNotFoundError.",
        "Fixture data was not used.",
    )

    coverage = calculate_evidence_coverage(
        evidence,
        ("IMPORT EXCEPTION", "moduleNotFoundError"),
    )
    forbidden_count = count_forbidden_evidence(
        evidence,
        ("fixture", "browser"),
    )

    assert coverage == 1.0
    assert forbidden_count == 1


@pytest.mark.parametrize(
    "category",
    [
        FailureCategory.TEST_ERROR,
        FailureCategory.TEST_FAILURE,
        FailureCategory.UNPARSED_FAILURE,
        FailureCategory.UNKNOWN,
    ],
)
def test_non_specific_categories_are_abstentions(
    category: FailureCategory,
) -> None:
    """Broad and uncertain results should count as abstentions."""
    assert is_abstention_category(category)


def test_category_metrics_reject_invalid_sequences() -> None:
    """Metrics require a non-empty pair with matching lengths."""
    with pytest.raises(ValueError, match="At least one"):
        calculate_category_metrics((), ())

    with pytest.raises(ValueError, match="equal lengths"):
        calculate_category_metrics(
            (FailureCategory.PASSED,),
            (),
        )
