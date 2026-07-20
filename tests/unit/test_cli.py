"""Tests for the Agent-Ops command-line interface."""

import json
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest

from agent_ops.cli import build_diagnostic_report, main
from agent_ops.models import (
    DiagnosticRun,
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
from agent_ops.workflow import ResumeCheckpointError
from agent_ops.workflow.state import AgentOpsState

RUN_ID = UUID("8ba9fe08-23c7-4eb0-8290-610dd0075e20")
STARTED_AT = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)
SNAPSHOT_SHA256 = "a" * 64


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
        snapshot_sha256=SNAPSHOT_SHA256,
    )


@pytest.fixture
def completed_run(tmp_path: Path) -> DiagnosticRun:
    """Return completed run metadata accepted by the public report boundary."""
    run = DiagnosticRun.start(
        run_id=RUN_ID,
        target_repository=tmp_path,
        agent_ops_version="0.1.0",
        started_at=STARTED_AT,
    )
    run = run.record_repository_version(
        target_repository=tmp_path,
        snapshot_sha256=SNAPSHOT_SHA256,
        git_commit_sha=None,
        recorded_at=STARTED_AT + timedelta(seconds=1),
    )
    return run.complete(completed_at=STARTED_AT + timedelta(seconds=2))


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
    completed_run: DiagnosticRun,
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
        "run": completed_run,
    }

    open_graph = _install_graph(monkeypatch, graph)

    main([str(tmp_path)])

    output = json.loads(capsys.readouterr().out)

    graph.invoke.assert_called_once_with(
        {
            "repository_path": str(tmp_path),
            "run_tests": False,
            "run_id": RUN_ID,
        },
        _graph_config(),
    )
    open_graph.assert_called_once_with(None, repository_path=str(tmp_path))

    assert output["repository"] == repository_profile.model_dump(mode="json")
    assert output["test_framework"] == framework_profile.model_dump(mode="json")
    assert output["run"] == completed_run.model_dump(mode="json")
    assert "test_execution" not in output
    assert "normalized_evidence" not in output
    assert "classification" not in output


def test_cli_runs_tests_when_explicitly_requested(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    normalized_evidence: NormalizedExecutionEvidence,
    passed_classification: FailureClassification,
    completed_run: DiagnosticRun,
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
        "run": completed_run,
    }

    open_graph = _install_graph(monkeypatch, graph)

    main([str(tmp_path), "--run-tests"])

    output = json.loads(capsys.readouterr().out)

    graph.invoke.assert_called_once_with(
        {
            "repository_path": str(tmp_path),
            "run_tests": True,
            "run_id": RUN_ID,
        },
        _graph_config(),
    )
    open_graph.assert_called_once_with(None, repository_path=str(tmp_path))

    assert output["repository"] == repository_profile.model_dump(mode="json")
    assert output["test_framework"] == framework_profile.model_dump(mode="json")
    assert output["test_execution"]["exit_code"] == 0
    assert output["test_execution"]["succeeded"] is True
    assert output["test_execution"]["summary"]["passed"] == 11
    assert output["normalized_evidence"] == normalized_evidence.model_dump(mode="json")
    assert output["classification"] == passed_classification.model_dump(mode="json")
    assert output["run"]["run_id"] == str(RUN_ID)
    assert output["run"]["status"] == "completed"
    assert output["run"]["provenance"]["target_repository_version"] == (f"sha256:{SNAPSHOT_SHA256}")


def test_cli_reports_failed_execution_without_discarding_raw_evidence(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    completed_run: DiagnosticRun,
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
        "run": completed_run,
    }

    _install_graph(monkeypatch, graph)

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
    completed_run: DiagnosticRun,
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
        "run": completed_run,
    }

    _install_graph(monkeypatch, graph)

    main([str(tmp_path), "--run-tests"])

    output = json.loads(capsys.readouterr().out)

    assert output["classification"]["category"] == "unsupported_framework"
    assert "test_execution" not in output
    assert "normalized_evidence" not in output


def test_diagnostic_report_rejects_partial_execution_state(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    completed_run: DiagnosticRun,
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
                "run": completed_run,
            }
        )


def test_cli_passes_explicit_run_id_to_graph(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    completed_run: DiagnosticRun,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should allow orchestration to assign a stable run identity."""
    graph = Mock()
    graph.invoke.return_value = {
        "repository_path": str(tmp_path),
        "run_tests": False,
        "repository_profile": repository_profile,
        "framework_profile": framework_profile,
        "run": completed_run,
    }
    open_graph = _install_graph(monkeypatch, graph)

    main([str(tmp_path), "--run-id", str(RUN_ID)])

    graph.invoke.assert_called_once_with(
        {
            "repository_path": str(tmp_path),
            "run_tests": False,
            "run_id": RUN_ID,
        },
        _graph_config(),
    )
    open_graph.assert_called_once_with(None, repository_path=str(tmp_path))
    assert json.loads(capsys.readouterr().out)["run"]["run_id"] == str(RUN_ID)


def test_cli_passes_custom_checkpoint_database_to_graph(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    completed_run: DiagnosticRun,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A custom SQLite location should cross the CLI boundary as a Path."""
    checkpoint_path = tmp_path.parent / "agent-ops-state.sqlite3"
    graph = Mock()
    graph.invoke.return_value = {
        "repository_path": str(tmp_path),
        "run_tests": False,
        "repository_profile": repository_profile,
        "framework_profile": framework_profile,
        "run": completed_run,
    }
    open_graph = _install_graph(monkeypatch, graph)

    main(
        [
            str(tmp_path),
            "--run-id",
            str(RUN_ID),
            "--checkpoint-db",
            str(checkpoint_path),
        ]
    )

    open_graph.assert_called_once_with(
        checkpoint_path,
        repository_path=str(tmp_path),
    )
    assert json.loads(capsys.readouterr().out)["run"]["status"] == "completed"


def test_cli_rejects_existing_checkpoint_thread(
    tmp_path: Path,
    completed_run: DiagnosticRun,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A new invocation must not silently replay an existing diagnostic run."""
    graph = Mock()
    _install_graph(monkeypatch, graph)
    graph.get_state.return_value.values = {"run": completed_run}

    with pytest.raises(SystemExit) as error:
        main([str(tmp_path), "--run-id", str(RUN_ID)])

    assert error.value.code == 2
    assert "Checkpoint history already exists" in capsys.readouterr().err
    graph.invoke.assert_not_called()


def test_cli_resumes_existing_safe_checkpoint(
    tmp_path: Path,
    repository_profile: RepositoryProfile,
    framework_profile: FrameworkProfile,
    completed_run: DiagnosticRun,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An explicit resume should continue with no new graph input."""
    persisted_state: AgentOpsState = {
        "repository_path": str(tmp_path),
        "run_tests": False,
        "run_id": RUN_ID,
    }
    resumed_state: AgentOpsState = {
        **persisted_state,
        "repository_profile": repository_profile,
        "framework_profile": framework_profile,
        "run": completed_run,
    }
    graph = Mock()
    open_graph = _install_graph(monkeypatch, graph)
    graph.get_state.return_value.values = persisted_state
    graph.get_state.return_value.next = ("inspect_repository",)
    graph.invoke.return_value = resumed_state
    validate_resume = Mock()
    monkeypatch.setattr("agent_ops.cli.validate_resume_checkpoint", validate_resume)

    main([str(tmp_path), "--resume", "--run-id", str(RUN_ID)])

    validate_resume.assert_called_once_with(
        persisted_state,
        ("inspect_repository",),
        repository_path=tmp_path,
        run_id=RUN_ID,
    )
    graph.invoke.assert_called_once_with(None, _graph_config())
    open_graph.assert_called_once_with(None, repository_path=str(tmp_path))
    assert json.loads(capsys.readouterr().out)["run"]["status"] == "completed"


def test_cli_resume_requires_explicit_run_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resume cannot generate a new identity for unknown checkpoint state."""
    with pytest.raises(SystemExit) as error:
        main([str(tmp_path), "--resume"])

    assert error.value.code == 2
    assert "--resume requires an explicit --run-id" in capsys.readouterr().err


def test_cli_resume_rejects_run_tests_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resume must use persisted intent instead of accepting new execution intent."""
    with pytest.raises(SystemExit) as error:
        main([str(tmp_path), "--resume", "--run-tests", "--run-id", str(RUN_ID)])

    assert error.value.code == 2
    assert "--run-tests cannot be combined with --resume" in capsys.readouterr().err


def test_cli_reports_unsafe_resume_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resume validation errors should become stable CLI usage errors."""
    graph = Mock()
    _install_graph(monkeypatch, graph)
    graph.get_state.return_value.values = {
        "repository_path": str(tmp_path),
        "run_tests": True,
        "run_id": RUN_ID,
    }
    graph.get_state.return_value.next = ("execute_tests",)
    monkeypatch.setattr(
        "agent_ops.cli.validate_resume_checkpoint",
        Mock(side_effect=ResumeCheckpointError("Unsafe checkpoint.")),
    )

    with pytest.raises(SystemExit) as error:
        main([str(tmp_path), "--resume", "--run-id", str(RUN_ID)])

    assert error.value.code == 2
    assert "Unsafe checkpoint" in capsys.readouterr().err
    graph.invoke.assert_not_called()


def _install_graph(
    monkeypatch: pytest.MonkeyPatch,
    graph: Mock,
) -> Mock:
    """Install one context-managed graph double with a deterministic generated ID."""
    open_graph = Mock(return_value=nullcontext(graph))
    graph.get_state.return_value.values = {}
    monkeypatch.setattr("agent_ops.cli.open_sqlite_diagnostic_graph", open_graph)
    monkeypatch.setattr("agent_ops.cli.uuid4", lambda: RUN_ID)
    return open_graph


def _graph_config() -> dict[str, dict[str, str]]:
    """Return the expected LangGraph thread configuration for the fixed run ID."""
    return {
        "configurable": {
            "thread_id": str(RUN_ID),
        }
    }
