"""Tests for pytest result parsing."""

from agent_ops.analysis import parse_pytest_result
from agent_ops.models import TestExecutionResult as ExecutionResult


def test_parse_pytest_result_reads_passing_summary() -> None:
    """A successful pytest summary should produce structured counts."""
    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="........... [100%]\n11 passed in 0.42s\n",
        stderr="",
        duration_seconds=1.0,
        timed_out=False,
    )

    result = parse_pytest_result(execution_result)

    assert result.summary_found is True
    assert result.passed == 11
    assert result.failed == 0
    assert result.errors == 0
    assert result.total_tests == 11
    assert result.failed_tests == ()


def test_parse_pytest_result_reads_failures_and_errors() -> None:
    """Failure evidence should include counts and test node IDs."""
    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        stdout=(
            ".FEs [100%]\n"
            "\n"
            "================ short test summary info ================\n"
            "FAILED tests/test_math.py::test_add - AssertionError\n"
            "ERROR tests/test_api.py::test_client - RuntimeError\n"
            "1 failed, 1 passed, 1 skipped, 1 error, "
            "2 warnings in 0.50s\n"
        ),
        stderr="",
        duration_seconds=1.0,
        timed_out=False,
    )

    result = parse_pytest_result(execution_result)

    assert result.summary_found is True
    assert result.passed == 1
    assert result.failed == 1
    assert result.errors == 1
    assert result.skipped == 1
    assert result.warnings == 2
    assert result.total_tests == 4
    assert result.failed_tests == (
        "tests/test_math.py::test_add",
    )
    assert result.error_tests == (
        "tests/test_api.py::test_client",
    )


def test_parse_pytest_result_handles_partial_output() -> None:
    """Incomplete output should not invent a test summary."""
    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=None,
        stdout="partial test output",
        stderr="",
        duration_seconds=120.0,
        timed_out=True,
    )

    result = parse_pytest_result(execution_result)

    assert result.summary_found is False
    assert result.summary_line is None
    assert result.total_tests == 0