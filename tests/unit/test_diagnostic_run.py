"""Tests for diagnostic-run identity, lifecycle, and provenance."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from agent_ops.models import (
    DiagnosticRun,
    DiagnosticRunStage,
    DiagnosticRunStatus,
)

RUN_ID = UUID("8ba9fe08-23c7-4eb0-8290-610dd0075e20")
STARTED_AT = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)
SNAPSHOT_SHA256 = "a" * 64
GIT_COMMIT_SHA = "b" * 40


def test_diagnostic_run_preserves_supplied_identity() -> None:
    """A caller-provided run ID should remain stable for the entire run."""
    run = DiagnosticRun.start(
        run_id=RUN_ID,
        target_repository=Path("/tmp/example"),
        agent_ops_version="0.1.0",
        started_at=STARTED_AT,
    )

    assert run.run_id == RUN_ID
    assert run.status is DiagnosticRunStatus.RUNNING
    assert run.stage is DiagnosticRunStage.INITIALIZED
    assert run.started_at == STARTED_AT
    assert run.finished_at is None
    assert run.provenance.agent_ops_version == "0.1.0"


def test_diagnostic_run_records_repository_provenance_and_completes() -> None:
    """A completed run should retain repository revision and content snapshot."""
    run = _started_run()
    inspected_at = STARTED_AT + timedelta(seconds=1)
    completed_at = STARTED_AT + timedelta(seconds=2)

    run = run.record_repository_version(
        target_repository=Path("/tmp/example"),
        snapshot_sha256=SNAPSHOT_SHA256,
        git_commit_sha=GIT_COMMIT_SHA,
        recorded_at=inspected_at,
    ).transition(
        DiagnosticRunStage.REPOSITORY_INSPECTION,
        transitioned_at=inspected_at,
    )
    run = run.complete(completed_at=completed_at)

    assert run.status is DiagnosticRunStatus.COMPLETED
    assert run.stage is DiagnosticRunStage.COMPLETED
    assert run.updated_at == completed_at
    assert run.finished_at == completed_at
    assert run.provenance.target_repository_version == f"sha256:{SNAPSHOT_SHA256}"
    assert run.provenance.target_repository_revision == GIT_COMMIT_SHA


def test_diagnostic_run_rejects_backward_stage_transition() -> None:
    """Lifecycle stages must move monotonically toward completion."""
    run = _started_run().transition(
        DiagnosticRunStage.FRAMEWORK_DETECTION,
        transitioned_at=STARTED_AT + timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="cannot move backward"):
        run.transition(
            DiagnosticRunStage.REPOSITORY_INSPECTION,
            transitioned_at=STARTED_AT + timedelta(seconds=2),
        )


def test_diagnostic_run_rejects_backward_timestamp() -> None:
    """Lifecycle timestamps must not move backward."""
    run = _started_run().transition(
        DiagnosticRunStage.REPOSITORY_INSPECTION,
        transitioned_at=STARTED_AT + timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="cannot move time backward"):
        run.transition(
            DiagnosticRunStage.FRAMEWORK_DETECTION,
            transitioned_at=STARTED_AT,
        )


def test_diagnostic_run_rejects_naive_timestamp() -> None:
    """Persistent lifecycle timestamps must always include a timezone."""
    with pytest.raises(ValidationError, match="must include a timezone"):
        DiagnosticRun.start(
            run_id=RUN_ID,
            target_repository=Path("/tmp/example"),
            agent_ops_version="0.1.0",
            started_at=datetime(2026, 7, 19, 12, 0),
        )


def test_diagnostic_run_cannot_complete_without_repository_provenance() -> None:
    """Completion should fail if the inspected target version is unknown."""
    with pytest.raises(
        ValidationError,
        match="requires target repository provenance",
    ):
        _started_run().complete(completed_at=STARTED_AT + timedelta(seconds=1))


def test_diagnostic_run_validates_repository_identifiers() -> None:
    """Malformed snapshot or Git identifiers should not cross the model boundary."""
    with pytest.raises(ValidationError):
        _started_run().record_repository_version(
            target_repository=Path("/tmp/example"),
            snapshot_sha256="not-a-sha256",
            git_commit_sha="not-a-git-sha",
            recorded_at=STARTED_AT + timedelta(seconds=1),
        )


def _started_run() -> DiagnosticRun:
    """Return one fixed running diagnostic run for lifecycle tests."""
    return DiagnosticRun.start(
        run_id=RUN_ID,
        target_repository=Path("/tmp/example"),
        agent_ops_version="0.1.0",
        started_at=STARTED_AT,
    )
