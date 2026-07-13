"""Tests for deterministic local evidence extraction."""

from agent_ops.analysis import extract_local_evidence
from agent_ops.models import TestExecutionResult as ExecutionResult


def test_extract_local_evidence_reads_diagnostic_details() -> None:
    """Known traceback structures should produce detailed evidence."""

    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        stdout=(
            "src/calculator.py:12: in add\n"
            '    raise ValueError("bad input")\n'
            "E   ValueError: bad input\n"
            "E   assert 1 == 2\n"
            "tests/test_api.py:8: "
            "DeprecationWarning: use new client\n"
            "FAILED tests/test_math.py::test_add - "
            "AssertionError: expected 2\n"
        ),
        stderr=(
            "Traceback (most recent call last):\n"
            '  File "C:\\repo\\src\\worker.py", '
            "line 44, in run\n"
            "RuntimeError: worker stopped\n"
        ),
        duration_seconds=1.0,
        timed_out=False,
    )

    result = extract_local_evidence(execution_result)

    assert result.exception_types == (
        "ValueError",
        "AssertionError",
        "RuntimeError",
    )
    assert result.assertion_messages == (
        "assert 1 == 2",
        "expected 2",
    )
    assert result.traceback_files == (
        "src/calculator.py",
        "C:\\repo\\src\\worker.py",
    )
    assert result.warning_messages == (
        "DeprecationWarning: use new client",
    )


def test_extract_local_evidence_ignores_unrecognized_output() -> None:
    """Unrecognized output should not produce invented evidence."""

    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=None,
        stdout="partial test output\nstill running\n",
        stderr="",
        duration_seconds=120.0,
        timed_out=True,
    )

    result = extract_local_evidence(execution_result)

    assert result.exception_types == ()
    assert result.assertion_messages == ()
    assert result.traceback_files == ()
    assert result.warning_messages == ()