"""Tests for the Agent-Ops command-line interface."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent_ops.cli import main
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
    graph = Mock()
    graph.invoke.return_value = {
        "repository_path": str(tmp_path),
        "run_tests": False,
        "repository_profile": repository_profile,
        "framework_profile": framework_profile,
    }

    monkeypatch.setattr(
        "agent_ops.cli.build_diagnostic_graph",
        lambda: graph,
    )

    main([str(tmp_path)])

    output = json.loads(capsys.readouterr().out)

    graph.invoke.assert_called_once_with(
        {
            "repository_path": str(tmp_path),
            "run_tests": False,
        }
    )

    assert output["repository"] == repository_profile.model_dump(mode="json")
    assert output["test_framework"] == framework_profile.model_dump(mode="json")
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
    test_summary = ResultSummary(
        summary_found=True,
        summary_line="11 passed in 0.42s",
        passed=11,
    )

    graph = Mock()
    graph.invoke.return_value = {
        "repository_path": str(tmp_path),
        "run_tests": True,
        "repository_profile": repository_profile,
        "framework_profile": framework_profile,
        "execution_result": execution_result,
        "test_summary": test_summary,
    }

    monkeypatch.setattr(
        "agent_ops.cli.build_diagnostic_graph",
        lambda: graph,
    )

    main([str(tmp_path), "--run-tests"])

    output = json.loads(capsys.readouterr().out)

    graph.invoke.assert_called_once_with(
        {
            "repository_path": str(tmp_path),
            "run_tests": True,
        }
    )

    assert output["repository"] == repository_profile.model_dump(mode="json")
    assert output["test_framework"] == framework_profile.model_dump(mode="json")
    assert output["test_execution"]["exit_code"] == 0
    assert output["test_execution"]["succeeded"] is True
    assert output["test_execution"]["summary"]["passed"] == 11
