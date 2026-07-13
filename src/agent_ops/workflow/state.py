"""State schema for the Agent-Ops diagnostic workflow."""

from typing import NotRequired, TypedDict

from agent_ops.models import (
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

    repository_profile: NotRequired[RepositoryProfile]
    framework_profile: NotRequired[TestFrameworkProfile]
    execution_result: NotRequired[TestExecutionResult]
    test_summary: NotRequired[TestResultSummary]
    normalized_evidence: NotRequired[NormalizedExecutionEvidence]
