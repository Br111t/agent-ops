"""Tests for the Agent-Ops diagnostic graph."""

from pathlib import Path
from unittest.mock import patch

from agent_ops.models import (
    RepositoryProfile,
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
