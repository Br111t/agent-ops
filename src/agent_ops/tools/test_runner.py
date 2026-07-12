"""Controlled execution of approved repository test commands."""

import subprocess
import sys
from pathlib import Path
from time import perf_counter

from agent_ops.models import (
    TestExecutionResult,
    TestFramework,
    TestFrameworkProfile,
)

APPROVED_PYTEST_COMMAND = (
    "python",
    "-m",
    "pytest",
    "-q",
)


def execute_approved_tests(
    repository_path: str | Path,
    framework_profile: TestFrameworkProfile,
    *,
    timeout_seconds: float = 120.0,
) -> TestExecutionResult:
    """Execute a detected and explicitly approved test command."""
    root_path = Path(repository_path).expanduser().resolve()

    if not root_path.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {root_path}"
        )

    if not root_path.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {root_path}"
        )

    approved_command = framework_profile.approved_command

    if (
        framework_profile.framework is not TestFramework.PYTEST
        or approved_command != APPROVED_PYTEST_COMMAND
    ):
        raise ValueError(
            "Test command is not approved for execution."
        )

    runtime_command = (
        sys.executable,
        *approved_command[1:],
    )

    started_at = perf_counter()

    try:
        completed_process = subprocess.run(
            runtime_command,
            cwd=root_path,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        duration_seconds = perf_counter() - started_at

        return TestExecutionResult(
            command=approved_command,
            exit_code=None,
            stdout=_as_text(error.stdout),
            stderr=_as_text(error.stderr),
            duration_seconds=duration_seconds,
            timed_out=True,
        )

    duration_seconds = perf_counter() - started_at

    return TestExecutionResult(
        command=approved_command,
        exit_code=completed_process.returncode,
        stdout=completed_process.stdout,
        stderr=completed_process.stderr,
        duration_seconds=duration_seconds,
        timed_out=False,
    )


def _as_text(value: str | bytes | None) -> str:
    """Normalize subprocess output into text."""
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode(errors="replace")

    return value