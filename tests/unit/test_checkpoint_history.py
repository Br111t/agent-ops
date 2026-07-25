"""Tests for stable diagnostic checkpoint-history queries."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import UUID

import pytest
from langgraph.types import StateSnapshot
from pydantic import ValidationError

from agent_ops.models import (
    DiagnosticCheckpointHistory,
    DiagnosticCheckpointRecord,
    DiagnosticCheckpointSource,
    DiagnosticRun,
    DiagnosticRunStage,
    DiagnosticRunStatus,
)
from agent_ops.workflow import CheckpointHistoryError, query_checkpoint_history

RUN_ID = UUID("8ba9fe08-23c7-4eb0-8290-610dd0075e20")
OTHER_RUN_ID = UUID("00918f6e-57ad-49fe-8e85-51801ac11a85")
CREATED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def test_query_returns_stable_newest_first_history() -> None:
    """Raw LangGraph snapshots should become immutable Agent-Ops records."""
    graph = Mock()
    graph.get_state_history.return_value = iter(
        (
            _snapshot(
                checkpoint_id="checkpoint-2",
                parent_checkpoint_id="checkpoint-1",
                step=1,
                created_at=CREATED_AT + timedelta(seconds=1),
                run=_running_run(),
                next_nodes=("inspect_repository",),
            ),
            _snapshot(
                checkpoint_id="checkpoint-1",
                step=-1,
                source="input",
                created_at=CREATED_AT,
                next_nodes=("__start__",),
            ),
        )
    )

    history = query_checkpoint_history(graph, RUN_ID, limit=20)

    graph.get_state_history.assert_called_once_with(
        {"configurable": {"thread_id": str(RUN_ID)}},
        limit=20,
    )
    assert history.run_id == RUN_ID
    assert history.checkpoint_count == 2
    assert [checkpoint.checkpoint_id for checkpoint in history.checkpoints] == [
        "checkpoint-2",
        "checkpoint-1",
    ]

    latest = history.checkpoints[0]
    assert latest.parent_checkpoint_id == "checkpoint-1"
    assert latest.step == 1
    assert latest.source is DiagnosticCheckpointSource.LOOP
    assert latest.run_status is DiagnosticRunStatus.RUNNING
    assert latest.run_stage is DiagnosticRunStage.INITIALIZED
    assert latest.next_nodes == ("inspect_repository",)

    oldest = history.checkpoints[-1]
    assert oldest.parent_checkpoint_id is None
    assert oldest.run_status is None
    assert oldest.run_stage is None
    assert oldest.source is DiagnosticCheckpointSource.INPUT
    assert history.model_dump(mode="json")["checkpoint_count"] == 2


def test_query_returns_empty_history_for_unknown_run() -> None:
    """An unknown run should produce an empty, well-formed result."""
    graph = Mock()
    graph.get_state_history.return_value = iter(())

    history = query_checkpoint_history(graph, RUN_ID)

    assert history.run_id == RUN_ID
    assert history.checkpoints == ()
    assert history.checkpoint_count == 0


def test_query_rejects_checkpoint_from_different_run() -> None:
    """A query must not silently combine history from different run identities."""
    graph = Mock()
    graph.get_state_history.return_value = iter(
        (
            _snapshot(
                checkpoint_id="checkpoint-1",
                step=-1,
                created_at=CREATED_AT,
                run_id=OTHER_RUN_ID,
            ),
        )
    )

    with pytest.raises(CheckpointHistoryError, match="different diagnostic run"):
        query_checkpoint_history(graph, RUN_ID)


def test_query_rejects_different_persisted_run_identity() -> None:
    """Checkpoint state must agree with its requested thread identity."""
    graph = Mock()
    graph.get_state_history.return_value = iter(
        (
            _snapshot(
                checkpoint_id="checkpoint-1",
                step=0,
                created_at=CREATED_AT,
                run=_running_run(run_id=OTHER_RUN_ID),
            ),
        )
    )

    with pytest.raises(CheckpointHistoryError, match="different persisted run identity"):
        query_checkpoint_history(graph, RUN_ID)


def test_query_rejects_malformed_checkpoint_metadata() -> None:
    """Missing trace metadata must not be replaced with invented values."""
    graph = Mock()
    snapshot = _snapshot(
        checkpoint_id="checkpoint-1",
        step=0,
        created_at=CREATED_AT,
    )
    graph.get_state_history.return_value = iter((snapshot._replace(metadata={}),))

    with pytest.raises(CheckpointHistoryError, match="source and step metadata"):
        query_checkpoint_history(graph, RUN_ID)


def test_query_requires_positive_limit() -> None:
    """History limits should be explicit positive counts."""
    graph = Mock()

    with pytest.raises(ValueError, match="at least 1"):
        query_checkpoint_history(graph, RUN_ID, limit=0)

    graph.get_state_history.assert_not_called()


def test_checkpoint_record_rejects_naive_timestamp() -> None:
    """Persistent checkpoint timestamps must retain timezone information."""
    with pytest.raises(ValidationError, match="must include a timezone"):
        DiagnosticCheckpointRecord(
            run_id=RUN_ID,
            checkpoint_id="checkpoint-1",
            step=-1,
            source=DiagnosticCheckpointSource.INPUT,
            created_at=datetime(2026, 7, 25, 12, 0),
        )


def test_history_model_rejects_different_run_identity() -> None:
    """A public history result must describe exactly one diagnostic run."""
    checkpoint = DiagnosticCheckpointRecord(
        run_id=OTHER_RUN_ID,
        checkpoint_id="checkpoint-1",
        step=-1,
        source=DiagnosticCheckpointSource.INPUT,
        created_at=CREATED_AT,
    )

    with pytest.raises(ValidationError, match="different run identity"):
        DiagnosticCheckpointHistory(
            run_id=RUN_ID,
            checkpoints=(checkpoint,),
        )


def test_query_rejects_history_that_is_not_newest_first() -> None:
    """Persisted history order must remain explicit and deterministic."""
    graph = Mock()
    graph.get_state_history.return_value = iter(
        (
            _snapshot(
                checkpoint_id="checkpoint-1",
                step=-1,
                created_at=CREATED_AT,
            ),
            _snapshot(
                checkpoint_id="checkpoint-2",
                step=0,
                created_at=CREATED_AT + timedelta(seconds=1),
            ),
        )
    )

    with pytest.raises(CheckpointHistoryError, match="history.*inconsistent"):
        query_checkpoint_history(graph, RUN_ID)


def _snapshot(
    *,
    checkpoint_id: str,
    step: int,
    created_at: datetime,
    parent_checkpoint_id: str | None = None,
    source: str = "loop",
    run: DiagnosticRun | None = None,
    run_id: UUID = RUN_ID,
    next_nodes: tuple[str, ...] = (),
) -> StateSnapshot:
    """Build one realistic LangGraph state snapshot."""
    parent_config = None
    if parent_checkpoint_id is not None:
        parent_config = _config(
            run_id=run_id,
            checkpoint_id=parent_checkpoint_id,
        )

    values = {"run_id": run_id}
    if run is not None:
        values["run"] = run

    return StateSnapshot(
        values=values,
        next=next_nodes,
        config=_config(run_id=run_id, checkpoint_id=checkpoint_id),
        metadata={
            "source": source,
            "step": step,
            "parents": {},
        },
        created_at=created_at.isoformat(),
        parent_config=parent_config,
        tasks=(),
        interrupts=(),
    )


def _config(
    *,
    run_id: UUID,
    checkpoint_id: str,
) -> dict[str, dict[str, str]]:
    """Return a checkpoint-specific LangGraph configuration."""
    return {
        "configurable": {
            "thread_id": str(run_id),
            "checkpoint_ns": "",
            "checkpoint_id": checkpoint_id,
        }
    }


def _running_run(*, run_id: UUID = RUN_ID) -> DiagnosticRun:
    """Return initialized run state for one post-node checkpoint."""
    return DiagnosticRun.start(
        run_id=run_id,
        target_repository="/tmp/repository",
        agent_ops_version="0.1.0",
        started_at=CREATED_AT,
    )
