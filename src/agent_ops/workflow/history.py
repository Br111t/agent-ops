"""Read-only queries for retained diagnostic checkpoint history."""

from collections.abc import Mapping
from uuid import UUID

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from pydantic import ValidationError

from agent_ops.models import (
    DiagnosticCheckpointHistory,
    DiagnosticCheckpointRecord,
    DiagnosticRun,
)
from agent_ops.workflow.checkpointing import build_checkpoint_config


class CheckpointHistoryError(ValueError):
    """Indicate that persisted checkpoint history is malformed or inconsistent."""


def query_checkpoint_history(
    graph: CompiledStateGraph,
    run_id: UUID,
    *,
    limit: int | None = None,
) -> DiagnosticCheckpointHistory:
    """Return stable checkpoint summaries for one run, newest first."""
    if limit is not None and limit < 1:
        raise ValueError("Checkpoint history limit must be at least 1.")

    config = build_checkpoint_config(run_id)
    snapshots = graph.get_state_history(config, limit=limit)
    checkpoints = tuple(_build_checkpoint_record(snapshot, run_id=run_id) for snapshot in snapshots)

    try:
        return DiagnosticCheckpointHistory(
            run_id=run_id,
            checkpoints=checkpoints,
        )
    except ValidationError as error:
        raise CheckpointHistoryError(
            f"Checkpoint history for run {run_id} is inconsistent."
        ) from error


def _build_checkpoint_record(
    snapshot: StateSnapshot,
    *,
    run_id: UUID,
) -> DiagnosticCheckpointRecord:
    """Convert one LangGraph snapshot into the stable Agent-Ops contract."""
    checkpoint_id = _get_config_value(snapshot.config, "checkpoint_id")
    thread_id = _get_config_value(snapshot.config, "thread_id")
    if thread_id != str(run_id):
        raise CheckpointHistoryError(
            f"Checkpoint {checkpoint_id} belongs to a different diagnostic run."
        )

    parent_checkpoint_id = None
    if snapshot.parent_config is not None:
        parent_thread_id = _get_config_value(snapshot.parent_config, "thread_id")
        if parent_thread_id != str(run_id):
            raise CheckpointHistoryError(
                f"Checkpoint {checkpoint_id} has a parent from a different diagnostic run."
            )
        parent_checkpoint_id = _get_config_value(
            snapshot.parent_config,
            "checkpoint_id",
        )

    metadata = snapshot.metadata
    if not isinstance(metadata, Mapping):
        raise CheckpointHistoryError(f"Checkpoint {checkpoint_id} does not contain valid metadata.")

    source = metadata.get("source")
    step = metadata.get("step")
    if not isinstance(source, str) or not isinstance(step, int) or isinstance(step, bool):
        raise CheckpointHistoryError(
            f"Checkpoint {checkpoint_id} does not contain valid source and step metadata."
        )

    if snapshot.created_at is None:
        raise CheckpointHistoryError(
            f"Checkpoint {checkpoint_id} does not contain a creation timestamp."
        )

    run = _get_persisted_run(
        snapshot,
        checkpoint_id=checkpoint_id,
        run_id=run_id,
    )
    try:
        return DiagnosticCheckpointRecord(
            run_id=run_id,
            checkpoint_id=checkpoint_id,
            parent_checkpoint_id=parent_checkpoint_id,
            step=step,
            source=source,
            created_at=snapshot.created_at,
            run_status=run.status if run is not None else None,
            run_stage=run.stage if run is not None else None,
            forked_from=run.forked_from if run is not None else None,
            next_nodes=snapshot.next,
        )
    except ValidationError as error:
        raise CheckpointHistoryError(
            f"Checkpoint {checkpoint_id} cannot be converted to the history contract."
        ) from error


def _get_config_value(config: Mapping[str, object], key: str) -> str:
    """Read one required string from a LangGraph checkpoint configuration."""
    configurable = config.get("configurable")
    if not isinstance(configurable, Mapping):
        raise CheckpointHistoryError("Checkpoint configuration is missing configurable values.")

    value = configurable.get(key)
    if not isinstance(value, str) or not value:
        raise CheckpointHistoryError(f"Checkpoint configuration is missing {key}.")

    return value


def _get_persisted_run(
    snapshot: StateSnapshot,
    *,
    checkpoint_id: str,
    run_id: UUID,
) -> DiagnosticRun | None:
    """Return validated run state when the checkpoint has reached initialization."""
    if not isinstance(snapshot.values, Mapping):
        raise CheckpointHistoryError(f"Checkpoint {checkpoint_id} does not contain mapping state.")

    saved_run_id = snapshot.values.get("run_id")
    if saved_run_id is not None and saved_run_id != run_id:
        raise CheckpointHistoryError(
            f"Checkpoint {checkpoint_id} contains a different state run identity."
        )

    run = snapshot.values.get("run")
    if run is None:
        return None
    if not isinstance(run, DiagnosticRun):
        raise CheckpointHistoryError(
            f"Checkpoint {checkpoint_id} does not contain a valid diagnostic run."
        )
    if run.run_id != run_id:
        raise CheckpointHistoryError(
            f"Checkpoint {checkpoint_id} contains a different persisted run identity."
        )

    return run
