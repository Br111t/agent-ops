"""Workflow nodes for the Agent-Ops diagnostic graph."""

from agent_ops.analysis import (
    classify_failure,
    normalize_execution_evidence,
    parse_pytest_result,
)
from agent_ops.models import (
    FailureClassification,
    NormalizedExecutionEvidence,
    RepositoryProfile,
    TestExecutionResult,
    TestFrameworkProfile,
    TestResultSummary,
)
from agent_ops.repository import detect_test_framework, scan_repository
from agent_ops.tools import execute_approved_tests
from agent_ops.workflow.state import AgentOpsState


def inspect_repository_node(
    state: AgentOpsState,
) -> dict[str, RepositoryProfile]:
    """Inspect the target repository and update its profile."""

    repository_profile = scan_repository(state["repository_path"])

    return {
        "repository_profile": repository_profile,
    }


def detect_framework_node(
    state: AgentOpsState,
) -> dict[str, TestFrameworkProfile]:
    """Detect the test framework used by the target repository."""

    framework_profile = detect_test_framework(
        state["repository_path"],
    )

    return {
        "framework_profile": framework_profile,
    }


def execute_tests_node(
    state: AgentOpsState,
) -> dict[str, TestExecutionResult]:
    """Execute the detected and approved test command."""

    execution_result = execute_approved_tests(
        state["repository_path"],
        state["framework_profile"],
    )

    return {
        "execution_result": execution_result,
    }


def parse_results_node(
    state: AgentOpsState,
) -> dict[str, TestResultSummary]:
    """Parse structured evidence from the captured test result."""

    test_summary = parse_pytest_result(
        state["execution_result"],
    )

    return {
        "test_summary": test_summary,
    }


def normalize_evidence_node(
    state: AgentOpsState,
) -> dict[str, NormalizedExecutionEvidence]:
    """Normalize execution metadata and parsed test evidence."""

    normalized_evidence = normalize_execution_evidence(
        state["execution_result"],
        state["test_summary"],
    )

    return {
        "normalized_evidence": normalized_evidence,
    }


def classify_result_node(
    state: AgentOpsState,
) -> dict[str, FailureClassification]:
    """Classify the diagnostic result using deterministic evidence."""

    classification = classify_failure(
        state["framework_profile"],
        state.get("normalized_evidence"),
    )

    return {
        "classification": classification,
    }
