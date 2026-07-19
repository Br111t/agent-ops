"""Controlled execution of approved repository test commands."""

import os
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from agent_ops.models import (
    TestExecutionResult,
    TestFrameworkProfile,
)
from agent_ops.safety import require_approved_test_command


def execute_approved_tests(
    repository_path: str | Path,
    framework_profile: TestFrameworkProfile,
    *,
    timeout_seconds: float = 120.0,
) -> TestExecutionResult:
    """Execute a detected and explicitly approved test command."""
    root_path = Path(repository_path).expanduser().resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {root_path}")

    if not root_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {root_path}")

    approved_command = require_approved_test_command(framework_profile)

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
            encoding="utf-8",
            errors="replace",
            env=_build_runtime_environment(),
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


def _build_runtime_environment() -> dict[str, str]:
    """Return an inherited environment with deterministic Python stream encoding."""
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _as_text(value: str | bytes | None) -> str:
    """Normalize subprocess output into text."""
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode(encoding="utf-8", errors="replace")

    return value
