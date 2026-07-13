"""Tests for normalized execution evidence."""

from agent_ops.analysis import normalize_execution_evidence
from agent_ops.models import (
    TestExecutionResult as ExecutionResult,
)
from agent_ops.models import (
    TestResultSummary as ResultSummary,
)


def test_normalize_execution_evidence_combines_known_fields() -> None:
    """Execution metadata and parsed results should form one evidence object."""

    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        stdout="1 failed, 2 passed in 0.40s\n",
        stderr="",
        duration_seconds=0.5,
        timed_out=False,
    )
    test_summary = ResultSummary(
        summary_found=True,
        summary_line="1 failed, 2 passed in 0.40s",
        passed=2,
        failed=1,
        warnings=3,
        failed_tests=("tests/test_math.py::test_add",),
    )

    result = normalize_execution_evidence(
        execution_result,
        test_summary,
    )

    assert result.command == (
        "python",
        "-m",
        "pytest",
        "-q",
    )
    assert result.exit_code == 1
    assert result.timed_out is False
    assert result.passed == 2
    assert result.failed == 1
    assert result.warning_count == 3
    assert result.failed_tests == (
        "tests/test_math.py::test_add",
    )
    assert result.exception_types == ()
    assert result.assertion_messages == ()
    assert result.traceback_files == ()
    assert result.warning_messages == ()


def test_normalize_execution_evidence_preserves_timeout_state() -> None:
    """Incomplete timed-out execution should remain explicit."""

    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=None,
        stdout="partial output",
        stderr="",
        duration_seconds=120.0,
        timed_out=True,
    )
    test_summary = ResultSummary(
        summary_found=False,
    )

    result = normalize_execution_evidence(
        execution_result,
        test_summary,
    )

    assert result.exit_code is None
    assert result.timed_out is True
    assert result.summary_found is False
    assert result.passed == 0
    assert result.failed == 0
    assert result.errors == 0