"""Public report models for repository diagnostics."""

from pydantic import BaseModel, ConfigDict, Field, computed_field

from agent_ops.models.execution_evidence import NormalizedExecutionEvidence
from agent_ops.models.failure_classification import FailureClassification
from agent_ops.models.repository import RepositoryProfile
from agent_ops.models.test_execution import TestExecutionResult
from agent_ops.models.test_framework import TestFrameworkProfile
from agent_ops.models.test_summary import TestResultSummary


class DiagnosticExecutionReport(BaseModel):
    """Public test-execution result with its parsed summary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    command: tuple[str, ...]
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = Field(ge=0.0)
    timed_out: bool = False
    summary: TestResultSummary

    @computed_field
    @property
    def succeeded(self) -> bool:
        """Return whether the test command completed successfully."""
        return not self.timed_out and self.exit_code == 0

    @classmethod
    def from_results(
        cls,
        execution_result: TestExecutionResult,
        test_summary: TestResultSummary,
    ) -> "DiagnosticExecutionReport":
        """Create a public execution report from captured internal results."""
        return cls(
            **execution_result.model_dump(),
            summary=test_summary,
        )


class DiagnosticReport(BaseModel):
    """Backward-compatible public result of one diagnostic workflow."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    repository: RepositoryProfile
    test_framework: TestFrameworkProfile
    test_execution: DiagnosticExecutionReport | None = None
    normalized_evidence: NormalizedExecutionEvidence | None = None
    classification: FailureClassification | None = None

    def to_public_dict(self) -> dict[str, object]:
        """Serialize present report sections while preserving nested null fields."""
        serialized = self.model_dump(mode="json")
        return {key: value for key, value in serialized.items() if value is not None}