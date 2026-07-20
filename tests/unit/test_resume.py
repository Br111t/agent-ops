"""Tests for safe diagnostic checkpoint resume validation."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from agent_ops.models import DiagnosticRun, DiagnosticRunStage
from agent_ops.models import TestExecutionResult as ExecutionResult
from agent_ops.models import TestFramework as Framework
from agent_ops.models import TestFrameworkProfile as FrameworkProfile
from agent_ops.repository import scan_repository
from agent_ops.workflow import ResumeCheckpointError, validate_resume_checkpoint
from agent_ops.workflow.state import AgentOpsState

RUN_ID = UUID("8ba9fe08-23c7-4eb0-8290-610dd0075e20")
STARTED_AT = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
def resumable_state(tmp_path: Path) -> AgentOpsState:
    """Return state persisted immediately after approved test execution."""
    repository_path = tmp_path / "repository"
    repository_path.mkdir()
    (repository_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    repository_profile = scan_repository(repository_path)
    snapshot_sha256 = repository_profile.snapshot_sha256
    assert snapshot_sha256 is not None

    run = DiagnosticRun.start(
        run_id=RUN_ID,
        target_repository=repository_path,
        agent_ops_version="0.1.0",
        started_at=STARTED_AT,
    )
    run = run.record_repository_version(
        target_repository=repository_path,
        snapshot_sha256=snapshot_sha256,
        git_commit_sha=None,
        recorded_at=STARTED_AT + timedelta(seconds=1),
    ).transition(
        DiagnosticRunStage.TEST_EXECUTION,
        transitioned_at=STARTED_AT + timedelta(seconds=2),
    )

    return {
        "repository_path": str(repository_path),
        "run_tests": True,
        "run_id": RUN_ID,
        "run": run,
        "repository_profile": repository_profile,
        "framework_profile": FrameworkProfile(
            framework=Framework.PYTEST,
            confidence=1.0,
            approved_command=("python", "-m", "pytest", "-q"),
        ),
        "execution_result": ExecutionResult(
            command=("python", "-m", "pytest", "-q"),
            exit_code=0,
            stdout="1 passed in 0.01s\n",
            duration_seconds=0.01,
        ),
    }


def test_resume_accepts_safe_pending_analysis_node(resumable_state: AgentOpsState) -> None:
    """Persisted evidence may continue into deterministic result parsing."""
    validate_resume_checkpoint(
        resumable_state,
        ("parse_results",),
        repository_path=resumable_state["repository_path"],
        run_id=RUN_ID,
    )


def test_resume_rejects_side_effecting_test_replay(resumable_state: AgentOpsState) -> None:
    """Resume must not rerun tests before replay protection exists."""
    with pytest.raises(ResumeCheckpointError, match="side-effecting operation"):
        validate_resume_checkpoint(
            resumable_state,
            ("execute_tests",),
            repository_path=resumable_state["repository_path"],
            run_id=RUN_ID,
        )


def test_resume_rejects_changed_repository(resumable_state: AgentOpsState) -> None:
    """Persisted evidence cannot be combined with different repository content."""
    repository_path = Path(resumable_state["repository_path"])
    (repository_path / "pytest.ini").write_text("[pytest]\naddopts = -q\n", encoding="utf-8")

    with pytest.raises(ResumeCheckpointError, match="content has changed"):
        validate_resume_checkpoint(
            resumable_state,
            ("parse_results",),
            repository_path=repository_path,
            run_id=RUN_ID,
        )


def test_resume_rejects_different_repository(
    tmp_path: Path,
    resumable_state: AgentOpsState,
) -> None:
    """A run may resume only against its original repository path."""
    other_repository = tmp_path / "other-repository"
    other_repository.mkdir()

    with pytest.raises(ResumeCheckpointError, match="does not match"):
        validate_resume_checkpoint(
            resumable_state,
            ("parse_results",),
            repository_path=other_repository,
            run_id=RUN_ID,
        )


def test_resume_rejects_completed_run(resumable_state: AgentOpsState) -> None:
    """A completed run has no work to continue."""
    run = resumable_state["run"]
    assert run is not None
    resumable_state["run"] = run.complete(
        completed_at=STARTED_AT + timedelta(seconds=3),
    )

    with pytest.raises(ResumeCheckpointError, match="already completed"):
        validate_resume_checkpoint(
            resumable_state,
            (),
            repository_path=resumable_state["repository_path"],
            run_id=RUN_ID,
        )


def test_resume_rejects_missing_checkpoint(tmp_path: Path) -> None:
    """An unknown run ID cannot be treated as resumable state."""
    with pytest.raises(ResumeCheckpointError, match="No checkpoint history"):
        validate_resume_checkpoint(
            {},
            (),
            repository_path=tmp_path,
            run_id=RUN_ID,
        )


def test_resume_rejects_malformed_partial_checkpoint(tmp_path: Path) -> None:
    """Incomplete internal state should fail closed before graph execution."""
    state: AgentOpsState = {
        "repository_path": str(tmp_path),
        "run_tests": True,
        "run_id": RUN_ID,
    }

    with pytest.raises(ResumeCheckpointError, match="missing state required"):
        validate_resume_checkpoint(
            state,
            ("parse_results",),
            repository_path=tmp_path,
            run_id=RUN_ID,
        )
