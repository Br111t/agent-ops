"""Tests for the Agent-Ops diagnostic graph."""

from pathlib import Path
from unittest.mock import patch

from agent_ops.models import (
    FailureCategory,
    FailureClassification,
    RepositoryProfile,
)
from agent_ops.models import (
    NormalizedExecutionEvidence as ExecutionEvidence,
)
from agent_ops.models import (
    TestExecutionResult as ExecutionResult,
)
from agent_ops.models import (
    TestFramework as Framework,
)
from agent_ops.models import (
    TestFrameworkProfile as FrameworkProfile,
)
from agent_ops.models import (
    TestResultSummary as ResultSummary,
)
from agent_ops.workflow import build_diagnostic_graph


def test_graph_stops_before_execution_when_tests_not_requested() -> None:
    """The graph should not execute tests unless explicitly requested."""

    repository_profile = RepositoryProfile(
        root_path=Path("/tmp/example"),
        repository_name="example",
        file_count=3,
        detected_languages=["Python"],
        configuration_files=["pyproject.toml"],
        test_files=["tests/test_example.py"],
        has_git_directory=True,
    )
    framework_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        approved_command=("python", "-m", "pytest", "-q"),
    )

    with (
        patch(
            "agent_ops.workflow.nodes.scan_repository",
            return_value=repository_profile,
        ),
        patch(
            "agent_ops.workflow.nodes.detect_test_framework",
            return_value=framework_profile,
        ),
        patch(
            "agent_ops.workflow.nodes.execute_approved_tests",
        ) as execute_tests,
    ):
        graph = build_diagnostic_graph()

        result = graph.invoke(
            {
                "repository_path": "/tmp/example",
                "run_tests": False,
            }
        )

    assert result["repository_profile"] == repository_profile
    assert result["framework_profile"] == framework_profile
    assert "execution_result" not in result
    assert "test_summary" not in result
    assert "normalized_evidence" not in result
    assert "classification" not in result
    execute_tests.assert_not_called()


def test_graph_executes_and_parses_when_tests_requested() -> None:
    """The graph should execute and parse tests when requested."""

    repository_profile = RepositoryProfile(
        root_path=Path("/tmp/example"),
        repository_name="example",
        file_count=3,
        detected_languages=["Python"],
        configuration_files=["pyproject.toml"],
        test_files=["tests/test_example.py"],
        has_git_directory=True,
    )
    framework_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        approved_command=("python", "-m", "pytest", "-q"),
    )
    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="2 passed in 0.10s\n",
        stderr="",
        duration_seconds=0.1,
        timed_out=False,
    )
    test_summary = ResultSummary(
        summary_found=True,
        summary_line="2 passed in 0.10s",
        passed=2,
    )
    normalized_evidence = ExecutionEvidence(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        timed_out=False,
        duration_seconds=0.1,
        summary_found=True,
        summary_line="2 passed in 0.10s",
        passed=2,
    )
    classification = FailureClassification(
        category=FailureCategory.PASSED,
        confidence=1.0,
        evidence=(
            "The approved test command exited with code 0.",
            "No test failures or errors were reported.",
        ),
        recommended_next_step=("Continue with reporting or additional diagnostic checks."),
    )

    with (
        patch(
            "agent_ops.workflow.nodes.scan_repository",
            return_value=repository_profile,
        ),
        patch(
            "agent_ops.workflow.nodes.detect_test_framework",
            return_value=framework_profile,
        ),
        patch(
            "agent_ops.workflow.nodes.execute_approved_tests",
            return_value=execution_result,
        ),
        patch(
            "agent_ops.workflow.nodes.parse_pytest_result",
            return_value=test_summary,
        ),
        patch(
            "agent_ops.workflow.nodes.normalize_execution_evidence",
            return_value=normalized_evidence,
        ),
        patch(
            "agent_ops.workflow.nodes.classify_failure",
            return_value=classification,
        ),
    ):
        graph = build_diagnostic_graph()

        result = graph.invoke(
            {
                "repository_path": "/tmp/example",
                "run_tests": True,
            }
        )

    assert result["repository_profile"] == repository_profile
    assert result["framework_profile"] == framework_profile
    assert result["execution_result"] == execution_result
    assert result["test_summary"] == test_summary
    assert result["normalized_evidence"] == normalized_evidence
    assert result["classification"] == classification


def test_graph_classifies_unknown_framework_without_execution() -> None:
    """Unknown frameworks should be classified without running tests."""

    repository_profile = RepositoryProfile(
        root_path=Path("/tmp/example"),
        repository_name="example",
        file_count=2,
        detected_languages=["JavaScript"],
        configuration_files=["package.json"],
        test_files=[],
        has_git_directory=True,
    )
    framework_profile = FrameworkProfile(
        framework=Framework.UNKNOWN,
        confidence=0.0,
        evidence=[],
        approved_command=None,
    )
    classification = FailureClassification(
        category=FailureCategory.UNSUPPORTED_FRAMEWORK,
        confidence=1.0,
        evidence=("Framework detection returned an unknown framework.",),
        missing_evidence=("No approved test command is available.",),
        recommended_next_step=(
            "Add support for the repository's test framework "
            "or provide an approved execution strategy."
        ),
    )

    with (
        patch(
            "agent_ops.workflow.nodes.scan_repository",
            return_value=repository_profile,
        ),
        patch(
            "agent_ops.workflow.nodes.detect_test_framework",
            return_value=framework_profile,
        ),
        patch(
            "agent_ops.workflow.nodes.execute_approved_tests",
        ) as execute_tests,
        patch(
            "agent_ops.workflow.nodes.classify_failure",
            return_value=classification,
        ) as classify,
    ):
        graph = build_diagnostic_graph()

        result = graph.invoke(
            {
                "repository_path": "/tmp/example",
                "run_tests": True,
            }
        )

    assert result["repository_profile"] == repository_profile
    assert result["framework_profile"] == framework_profile
    assert result["classification"] == classification
    assert "execution_result" not in result
    assert "test_summary" not in result
    assert "normalized_evidence" not in result

    execute_tests.assert_not_called()
    classify.assert_called_once_with(
        framework_profile,
        None,
    )
