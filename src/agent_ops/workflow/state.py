"""State schema for the Agent-Ops diagnostic workflow."""

from typing import NotRequired, TypedDict
from uuid import UUID

from agent_ops.models import (
    DiagnosticRun,
    FailureClassification,
    NormalizedExecutionEvidence,
    RepositoryProfile,
    TestExecutionResult,
    TestFrameworkProfile,
    TestResultSummary,
)


class AgentOpsState(TypedDict):
    """Shared state passed between Agent-Ops workflow nodes."""

    repository_path: str
    run_tests: bool
    run_id: NotRequired[UUID]

    run: NotRequired[DiagnosticRun]
    repository_profile: NotRequired[RepositoryProfile]
    framework_profile: NotRequired[TestFrameworkProfile]
    execution_result: NotRequired[TestExecutionResult]
    test_summary: NotRequired[TestResultSummary]
    normalized_evidence: NotRequired[NormalizedExecutionEvidence]
    classification: NotRequired[FailureClassification]
