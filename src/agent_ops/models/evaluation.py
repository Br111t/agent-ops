"""Models describing deterministic classification evaluations."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_ops.models.execution_evidence import NormalizedExecutionEvidence
from agent_ops.models.failure_classification import FailureCategory
from agent_ops.models.test_framework import TestFrameworkProfile


class EvaluationSourceType(StrEnum):
    """Provenance categories for evaluation cases."""

    SYNTHETIC = "synthetic"
    SANITIZED_REAL = "sanitized_real"
    REGRESSION = "regression"


class ClassificationEvaluationCase(BaseModel):
    """One trusted failure-classification example."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    case_id: str = Field(min_length=1)
    source_type: EvaluationSourceType
    description: str = Field(min_length=1)
    framework_profile: TestFrameworkProfile
    normalized_evidence: NormalizedExecutionEvidence | None
    expected_category: FailureCategory
    required_evidence_markers: tuple[str, ...] = ()
    forbidden_evidence_markers: tuple[str, ...] = ()
    expected_abstention: bool = False
    notes: str | None = None


class ClassificationEvaluationDataset(BaseModel):
    """A versioned collection of classification evaluation cases."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    cases: tuple[ClassificationEvaluationCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> "ClassificationEvaluationDataset":
        """Require stable, unique identifiers within a dataset version."""
        case_ids = [case.case_id for case in self.cases]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Evaluation case IDs must be unique.")

        return self


class CategoryEvaluationMetrics(BaseModel):
    """Precision and recall measurements for one failure category."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    category: FailureCategory
    support: int = Field(ge=0)
    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)


class ClassificationCaseEvaluationResult(BaseModel):
    """Measured result for one classification evaluation case."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    case_id: str = Field(min_length=1)
    expected_category: FailureCategory
    actual_category: FailureCategory
    category_correct: bool
    expected_abstention: bool
    actual_abstention: bool
    abstention_correct: bool
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    unsupported_evidence_count: int = Field(ge=0)
    evidence_correct: bool
    confidence: float = Field(ge=0.0, le=1.0)
    duration_seconds: float = Field(ge=0.0)
    passed: bool


class ClassificationEvaluationReport(BaseModel):
    """Aggregate report for a deterministic classification experiment."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    dataset_name: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    system_version: str = Field(min_length=1)
    total_cases: int = Field(gt=0)
    passed_cases: int = Field(ge=0)
    category_accuracy: float = Field(ge=0.0, le=1.0)
    abstention_accuracy: float = Field(ge=0.0, le=1.0)
    evidence_accuracy: float = Field(ge=0.0, le=1.0)
    macro_precision: float = Field(ge=0.0, le=1.0)
    macro_recall: float = Field(ge=0.0, le=1.0)
    macro_f1: float = Field(ge=0.0, le=1.0)
    duration_seconds: float = Field(ge=0.0)
    confusion_matrix: dict[str, dict[str, int]]
    categories: tuple[CategoryEvaluationMetrics, ...]
    cases: tuple[ClassificationCaseEvaluationResult, ...]