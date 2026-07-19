"""Tests for controlled test execution."""

import subprocess
from pathlib import Path

import pytest

from agent_ops.models import (
    TestFramework as Framework,
)
from agent_ops.models import (
    TestFrameworkProfile as FrameworkProfile,
)
from agent_ops.tools import execute_approved_tests


@pytest.fixture
def pytest_profile() -> FrameworkProfile:
    """Return an approved pytest framework profile."""
    return FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=0.95,
        evidence=["pytest configuration found"],
        approved_command=("python", "-m", "pytest", "-q"),
    )


def test_execute_approved_tests_captures_result(
    tmp_path: Path,
    pytest_profile: FrameworkProfile,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approved test execution should capture process evidence."""
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    completed_process = subprocess.CompletedProcess(
        args=["python", "-m", "pytest", "-q"],
        returncode=0,
        stdout="6 passed",
        stderr="",
    )

    def capture_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["errors"] == "replace"
        assert kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
        return completed_process

    monkeypatch.setattr(subprocess, "run", capture_run)

    result = execute_approved_tests(
        tmp_path,
        pytest_profile,
    )

    assert result.exit_code == 0
    assert result.stdout == "6 passed"
    assert result.stderr == ""
    assert result.timed_out is False
    assert result.succeeded is True


def test_execute_approved_tests_rejects_unapproved_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modified or unrestricted commands must not execute."""
    unapproved_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=0.95,
        evidence=["pytest configuration found"],
        approved_command=(
            "python",
            "-m",
            "pytest",
            "-q",
            "--unexpected-option",
        ),
    )

    def fail_if_executed(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unapproved command reached subprocess execution.")

    monkeypatch.setattr(subprocess, "run", fail_if_executed)

    with pytest.raises(
        ValueError,
        match="not approved",
    ):
        execute_approved_tests(
            tmp_path,
            unapproved_profile,
        )


def test_execute_approved_tests_records_timeout(
    tmp_path: Path,
    pytest_profile: FrameworkProfile,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A timeout should return structured evidence."""

    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd=["python", "-m", "pytest", "-q"],
            timeout=1,
            output="partial output",
            stderr="timeout error",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        raise_timeout,
    )

    result = execute_approved_tests(
        tmp_path,
        pytest_profile,
        timeout_seconds=1,
    )

    assert result.exit_code is None
    assert result.stdout == "partial output"
    assert result.stderr == "timeout error"
    assert result.timed_out is True
    assert result.succeeded is False
