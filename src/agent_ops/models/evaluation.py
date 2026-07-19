"""Models describing deterministic classification evaluations."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from agent_ops.models.execution_evidence import NormalizedExecutionEvidence
from agent_ops.models.failure_classification import FailureCategory
from agent_ops.models.test_framework import TestFrameworkProfile


class EvaluationSourceType(StrEnum):
    """Provenance categories for evaluation cases."""

    SYNTHETIC = "synthetic"
    SANITIZED_REAL = "sanitized_real"
    REGRESSION = "regression"


class EvaluationCaseChange(StrEnum):
    """Outcome changes between baseline and candidate evaluation cases."""

    REGRESSION = "regression"
    IMPROVEMENT = "improvement"
    UNCHANGED = "unchanged"


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

    @model_validator(mode="after")
    def validate_case_totals(self) -> "ClassificationEvaluationReport":
        """Require aggregate counts to match the serialized case results."""
        case_ids = tuple(case.case_id for case in self.cases)

        if len(self.cases) != self.total_cases:
            raise ValueError("Evaluation case count must match total_cases.")

        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Evaluation report case IDs must be unique.")

        if sum(case.passed for case in self.cases) != self.passed_cases:
            raise ValueError("Passing case count must match passed_cases.")

        return self


class ClassificationCaseComparison(BaseModel):
    """Comparison of one case across baseline and candidate reports."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    case_id: str = Field(min_length=1)
    expected_category: FailureCategory
    baseline_actual_category: FailureCategory
    candidate_actual_category: FailureCategory
    baseline_passed: bool
    candidate_passed: bool
    change: EvaluationCaseChange


class ClassificationEvaluationComparison(BaseModel):
    """Machine-readable comparison and gate result for two evaluations."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    dataset_name: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    baseline_system_version: str = Field(min_length=1)
    candidate_system_version: str = Field(min_length=1)
    total_cases: int = Field(gt=0)
    passed_cases_delta: int
    category_accuracy_delta: float = Field(ge=-1.0, le=1.0)
    abstention_accuracy_delta: float = Field(ge=-1.0, le=1.0)
    evidence_accuracy_delta: float = Field(ge=-1.0, le=1.0)
    macro_f1_delta: float = Field(ge=-1.0, le=1.0)
    duration_seconds_delta: float
    cases: tuple[ClassificationCaseComparison, ...]
    gate_failures: tuple[str, ...] = ()

    @computed_field
    @property
    def regression_case_ids(self) -> tuple[str, ...]:
        """Return case identifiers that changed from passing to failing."""
        return tuple(
            case.case_id for case in self.cases if case.change is EvaluationCaseChange.REGRESSION
        )

    @computed_field
    @property
    def improvement_case_ids(self) -> tuple[str, ...]:
        """Return case identifiers that changed from failing to passing."""
        return tuple(
            case.case_id for case in self.cases if case.change is EvaluationCaseChange.IMPROVEMENT
        )

    @computed_field
    @property
    def gate_passed(self) -> bool:
        """Return whether the candidate satisfies every comparison gate."""
        return not self.gate_failures

    @model_validator(mode="after")
    def validate_case_count(self) -> "ClassificationEvaluationComparison":
        """Require one comparison result per evaluation case."""
        if len(self.cases) != self.total_cases:
            raise ValueError("Comparison case count must match total_cases.")

        return self
