"""Tests for the Agent-Ops command-line interface."""

import json
from pathlib import Path

import pytest

from agent_ops.__main__ import main
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


@pytest.fixture
def repository_profile(tmp_path: Path) -> RepositoryProfile:
    """Return a sample repository profile."""
    return RepositoryProfile(
        root_path=tmp_path,
        repository_name="sample",
        file_count=1,
        detected_languages=["Python"],
        configuration_files=["pyproject.toml"],
        test_files=["tests/test_sample.py"],
        has_git_directory=True,
    )


@pytest.fixture
def framework_profile() -> FrameworkProfile:
    """Return an approved pytest profile."""
    return FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=0.95,
        evidence=["pytest configuration found"],
        approved_command=("python", "-m", "pytest", "-q"),
    )


def test_cli_does_not_run_tests_by_default(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Repository inspection should remain read-only by default."""
    monkeypatch.setattr(
        "agent_ops.__main__.scan_repository",
        lambda path: repository_profile,
    )
    monkeypatch.setattr(
        "agent_ops.__main__.detect_test_framework",
        lambda path: framework_profile,
    )

    def unexpected_execution(*args: object, **kwargs: object) -> None:
        raise AssertionError("Tests must not run without --run-tests")

    monkeypatch.setattr(
        "agent_ops.__main__.execute_approved_tests",
        unexpected_execution,
    )

    main([str(tmp_path)])

    output = json.loads(capsys.readouterr().out)

    assert "repository" in output
    assert "test_framework" in output
    assert "test_execution" not in output


def test_cli_runs_tests_when_explicitly_requested(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The --run-tests flag should trigger approved execution."""
    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="11 passed in 0.42s\n",
        stderr="",
        duration_seconds=0.5,
        timed_out=False,
    )

    monkeypatch.setattr(
        "agent_ops.__main__.scan_repository",
        lambda path: repository_profile,
    )
    monkeypatch.setattr(
        "agent_ops.__main__.detect_test_framework",
        lambda path: framework_profile,
    )
    monkeypatch.setattr(
        "agent_ops.__main__.execute_approved_tests",
        lambda path, profile: execution_result,
    )

    main([str(tmp_path), "--run-tests"])

    output = json.loads(capsys.readouterr().out)

    assert output["test_execution"]["exit_code"] == 0
    assert output["test_execution"]["succeeded"] is True
    assert output["test_execution"]["stdout"] == "11 passed in 0.42s\n"
    assert output["test_execution"]["summary"]["passed"] == 11
    assert output["test_execution"]["summary"]["failed"] == 0
    assert output["test_execution"]["summary"]["total_tests"] == 11