"""Tests for the Agent-Ops command-line interface."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent_ops.cli import build_diagnostic_report, main
from agent_ops.models import (
    FailureCategory,
    FailureClassification,
    NormalizedExecutionEvidence,
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


@pytest.fixture
def normalized_evidence() -> NormalizedExecutionEvidence:
    """Return normalized evidence for a successful test run."""
    return NormalizedExecutionEvidence(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        timed_out=False,
        duration_seconds=0.5,
        summary_found=True,
        summary_line="11 passed in 0.42s",
        passed=11,
    )


@pytest.fixture
def passed_classification() -> FailureClassification:
    """Return an evidence-supported passing classification."""
    return FailureClassification(
        category=FailureCategory.PASSED,
        confidence=1.0,
        evidence=(
            "The approved test command exited with code 0.",
            "No test failures or errors were reported.",
        ),
        recommended_next_step=("Continue with reporting or additional diagnostic checks."),
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
    assert "normalized_evidence" not in output
    assert "classification" not in output


def test_cli_runs_tests_when_explicitly_requested(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    normalized_evidence: NormalizedExecutionEvidence,
    passed_classification: FailureClassification,
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
        "normalized_evidence": normalized_evidence,
        "classification": passed_classification,
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
    assert output["normalized_evidence"] == normalized_evidence.model_dump(mode="json")
    assert output["classification"] == passed_classification.model_dump(mode="json")


def test_cli_reports_failed_execution_without_discarding_raw_evidence(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A failed command should retain raw and interpreted evidence."""
    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        stdout="FAILED tests/test_sample.py::test_example\n",
        stderr="AssertionError: expected ready\n",
        duration_seconds=0.7,
        timed_out=False,
    )
    test_summary = ResultSummary(
        summary_found=True,
        summary_line="1 failed in 0.60s",
        failed=1,
        failed_tests=("tests/test_sample.py::test_example",),
    )
    normalized_evidence = NormalizedExecutionEvidence(
        command=execution_result.command,
        exit_code=execution_result.exit_code,
        timed_out=execution_result.timed_out,
        duration_seconds=execution_result.duration_seconds,
        summary_found=True,
        summary_line=test_summary.summary_line,
        failed=1,
        failed_tests=test_summary.failed_tests,
        exception_types=("AssertionError",),
        assertion_messages=("expected ready",),
    )
    classification = FailureClassification(
        category=FailureCategory.ASSERTION_FAILURE,
        confidence=1.0,
        evidence=("AssertionError was captured in the test output.",),
        recommended_next_step="Review the failed assertion and application state.",
    )

    graph = Mock()
    graph.invoke.return_value = {
        "repository_path": str(tmp_path),
        "run_tests": True,
        "repository_profile": repository_profile,
        "framework_profile": framework_profile,
        "execution_result": execution_result,
        "test_summary": test_summary,
        "normalized_evidence": normalized_evidence,
        "classification": classification,
    }

    monkeypatch.setattr(
        "agent_ops.cli.build_diagnostic_graph",
        lambda: graph,
    )

    main([str(tmp_path), "--run-tests"])

    output = json.loads(capsys.readouterr().out)

    assert output["test_execution"]["succeeded"] is False
    assert output["test_execution"]["stdout"] == execution_result.stdout
    assert output["test_execution"]["stderr"] == execution_result.stderr
    assert output["normalized_evidence"]["failed"] == 1
    assert output["classification"]["category"] == "assertion_failure"


def test_cli_classifies_unsupported_framework_without_execution(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsupported frameworks should produce a diagnostic instead of crashing."""
    framework_profile = FrameworkProfile(
        framework=Framework.UNKNOWN,
        confidence=0.0,
        evidence=[],
        approved_command=None,
    )
    classification = FailureClassification(
        category=FailureCategory.UNSUPPORTED_FRAMEWORK,
        confidence=1.0,
        evidence=("Framework detection returned an unknown framework.",),
        missing_evidence=("No approved test command is available.",),
        recommended_next_step=(
            "Add support for the repository's test framework or provide an "
            "approved execution strategy."
        ),
    )

    graph = Mock()
    graph.invoke.return_value = {
        "repository_path": str(tmp_path),
        "run_tests": True,
        "repository_profile": repository_profile,
        "framework_profile": framework_profile,
        "classification": classification,
    }

    monkeypatch.setattr(
        "agent_ops.cli.build_diagnostic_graph",
        lambda: graph,
    )

    main([str(tmp_path), "--run-tests"])

    output = json.loads(capsys.readouterr().out)

    assert output["classification"]["category"] == "unsupported_framework"
    assert "test_execution" not in output
    assert "normalized_evidence" not in output


def test_diagnostic_report_rejects_partial_execution_state(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
) -> None:
    """Execution and parsed summary must cross the public boundary together."""
    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        duration_seconds=0.1,
    )

    with pytest.raises(
        ValueError,
        match="Execution result and test summary must be present together",
    ):
        build_diagnostic_report(
            {
                "repository_path": str(tmp_path),
                "run_tests": True,
                "repository_profile": repository_profile,
                "framework_profile": framework_profile,
                "execution_result": execution_result,
            }
        )