"""Workflow nodes for the Agent-Ops diagnostic graph."""

from agent_ops.analysis import parse_pytest_result
from agent_ops.models import (
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
