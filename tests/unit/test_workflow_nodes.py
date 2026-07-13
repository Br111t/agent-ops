"""Tests for Agent-Ops workflow nodes."""

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
from agent_ops.workflow.nodes import (
    classify_result_node,
    detect_framework_node,
    execute_tests_node,
    inspect_repository_node,
    normalize_evidence_node,
    parse_results_node,
)


def test_inspect_repository_node_returns_profile() -> None:
    """Repository inspection should return a partial state update."""

    expected = RepositoryProfile(
        root_path=Path("/tmp/example"),
        repository_name="example",
        file_count=3,
        detected_languages=["Python"],
        configuration_files=["pyproject.toml"],
        test_files=["tests/test_example.py"],
        has_git_directory=True,
    )

    with patch(
        "agent_ops.workflow.nodes.scan_repository",
        return_value=expected,
    ) as scan_repository:
        result = inspect_repository_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": False,
            }
        )

    assert result == {"repository_profile": expected}
    scan_repository.assert_called_once_with("/tmp/example")


def test_detect_framework_node_returns_profile() -> None:
    """Framework detection should return a partial state update."""

    expected = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        evidence=["pyproject.toml configures pytest"],
        approved_command=("python", "-m", "pytest", "-q"),
    )

    with patch(
        "agent_ops.workflow.nodes.detect_test_framework",
        return_value=expected,
    ) as detect_test_framework:
        result = detect_framework_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": False,
            }
        )

    assert result == {"framework_profile": expected}
    detect_test_framework.assert_called_once_with("/tmp/example")


def test_execute_tests_node_returns_execution_result() -> None:
    """Approved execution should return captured test evidence."""

    framework_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        approved_command=("python", "-m", "pytest", "-q"),
    )
    expected = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="2 passed in 0.10s\n",
        stderr="",
        duration_seconds=0.1,
        timed_out=False,
    )

    with patch(
        "agent_ops.workflow.nodes.execute_approved_tests",
        return_value=expected,
    ) as execute_approved_tests:
        result = execute_tests_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": True,
                "framework_profile": framework_profile,
            }
        )

    assert result == {"execution_result": expected}
    execute_approved_tests.assert_called_once_with(
        "/tmp/example",
        framework_profile,
    )


def test_parse_results_node_returns_summary() -> None:
    """Captured output should be converted into structured evidence."""

    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="2 passed in 0.10s\n",
        stderr="",
        duration_seconds=0.1,
        timed_out=False,
    )
    expected = ResultSummary(
        summary_found=True,
        summary_line="2 passed in 0.10s",
        passed=2,
    )

    with patch(
        "agent_ops.workflow.nodes.parse_pytest_result",
        return_value=expected,
    ) as parse_pytest_result:
        result = parse_results_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": True,
                "execution_result": execution_result,
            }
        )

    assert result == {"test_summary": expected}
    parse_pytest_result.assert_called_once_with(execution_result)


def test_normalize_evidence_node_combines_execution_evidence() -> None:
    """The normalization node should return consistent execution evidence."""

    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        stdout="1 failed in 0.20s\n",
        stderr="",
        duration_seconds=0.3,
        timed_out=False,
    )
    test_summary = ResultSummary(
        summary_found=True,
        summary_line="1 failed in 0.20s",
        failed=1,
    )
    normalized_evidence = ExecutionEvidence(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        timed_out=False,
        duration_seconds=0.3,
        summary_found=True,
        summary_line="1 failed in 0.20s",
        failed=1,
    )

    with patch(
        "agent_ops.workflow.nodes.normalize_execution_evidence",
        return_value=normalized_evidence,
    ) as normalize:
        result = normalize_evidence_node(
            {
                "repository_path": ".",
                "run_tests": True,
                "execution_result": execution_result,
                "test_summary": test_summary,
            }
        )

    assert result == {
        "normalized_evidence": normalized_evidence,
    }
    normalize.assert_called_once_with(
        execution_result,
        test_summary,
    )


def test_classify_result_node_returns_classification() -> None:
    """Normalized evidence should produce a deterministic classification."""

    framework_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        approved_command=("python", "-m", "pytest", "-q"),
    )
    normalized_evidence = ExecutionEvidence(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        timed_out=False,
        duration_seconds=0.3,
        summary_found=True,
        summary_line="1 failed in 0.20s",
        failed=1,
    )
    expected = FailureClassification(
        category=FailureCategory.TEST_FAILURE,
        confidence=0.99,
        evidence=("Parsed output reported 1 failed test(s).",),
        recommended_next_step=(
            "Inspect assertion messages and affected test cases."
        ),
    )

    with patch(
        "agent_ops.workflow.nodes.classify_failure",
        return_value=expected,
    ) as classify:
        result = classify_result_node(
            {
                "repository_path": ".",
                "run_tests": True,
                "framework_profile": framework_profile,
                "normalized_evidence": normalized_evidence,
            }
        )

    assert result == {
        "classification": expected,
    }
    classify.assert_called_once_with(
        framework_profile,
        normalized_evidence,
    )