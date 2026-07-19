"""Tests for deterministic failure-classification evaluation."""

import pytest
from evals.datasets import FAILURE_CLASSIFICATION_DATASET
from pydantic import ValidationError

from agent_ops.evaluation import evaluate_failure_classification
from agent_ops.models import (
    ClassificationEvaluationCase,
    ClassificationEvaluationDataset,
    EvaluationSourceType,
    FailureCategory,
)
from agent_ops.models import (
    TestFramework as Framework,
)
from agent_ops.models import (
    TestFrameworkProfile as FrameworkProfile,
)


def test_foundation_dataset_covers_every_failure_category() -> None:
    """The first dataset should represent every public category."""
    represented = {case.expected_category for case in FAILURE_CLASSIFICATION_DATASET.cases}

    assert represented == set(FailureCategory)


def test_foundation_dataset_matches_current_classifier() -> None:
    """The checked-in baseline should pass category and evidence checks."""
    report = evaluate_failure_classification(
        FAILURE_CLASSIFICATION_DATASET,
        system_version="test-version",
    )

    assert report.total_cases == len(FAILURE_CLASSIFICATION_DATASET.cases)
    assert report.passed_cases == report.total_cases
    assert report.category_accuracy == 1.0
    assert report.abstention_accuracy == 1.0
    assert report.evidence_accuracy == 1.0
    assert report.macro_precision == 1.0
    assert report.macro_recall == 1.0
    assert report.macro_f1 == 1.0
    assert all(case.passed for case in report.cases)


def test_evaluation_report_serializes_to_json() -> None:
    """Evaluation output should preserve the public structured contract."""
    report = evaluate_failure_classification(
        FAILURE_CLASSIFICATION_DATASET,
        system_version="serialization-test",
    )

    serialized = report.model_dump(mode="json")

    assert serialized["dataset_version"] == "1.0.0"
    assert serialized["system_version"] == "serialization-test"
    assert serialized["cases"][0]["expected_category"]
    assert serialized["confusion_matrix"]["passed"]["passed"] == 2


def test_dataset_rejects_duplicate_case_ids() -> None:
    """A dataset version must identify every case uniquely."""
    framework_profile = FrameworkProfile(
        framework=Framework.UNKNOWN,
        confidence=0.0,
        evidence=[],
        approved_command=None,
    )
    case = ClassificationEvaluationCase(
        case_id="duplicate",
        source_type=EvaluationSourceType.SYNTHETIC,
        description="Duplicate identifier fixture.",
        framework_profile=framework_profile,
        normalized_evidence=None,
        expected_category=FailureCategory.UNSUPPORTED_FRAMEWORK,
    )

    with pytest.raises(ValidationError, match="must be unique"):
        ClassificationEvaluationDataset(
            name="duplicates",
            version="1.0.0",
            cases=(case, case),
        )
