"""Safe creation of new diagnostic runs from historical checkpoints."""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot

from agent_ops.models import DiagnosticRun, DiagnosticRunStage
from agent_ops.workflow.checkpointing import build_checkpoint_config
from agent_ops.workflow.resume import ResumeCheckpointError, validate_resume_checkpoint
from agent_ops.workflow.state import AgentOpsState

_SOURCE_NODE_BY_STAGE = {
    DiagnosticRunStage.INITIALIZED: "initialize_run",
    DiagnosticRunStage.REPOSITORY_INSPECTION: "inspect_repository",
    DiagnosticRunStage.FRAMEWORK_DETECTION: "detect_framework",
    DiagnosticRunStage.TEST_EXECUTION: "execute_tests",
    DiagnosticRunStage.RESULT_PARSING: "parse_results",
    DiagnosticRunStage.EVIDENCE_NORMALIZATION: "normalize_evidence",
    DiagnosticRunStage.FAILURE_CLASSIFICATION: "classify_result",
}
_NEXT_NODES_BY_STAGE = {
    DiagnosticRunStage.INITIALIZED: frozenset({("inspect_repository",)}),
    DiagnosticRunStage.REPOSITORY_INSPECTION: frozenset({("detect_framework",)}),
    DiagnosticRunStage.FRAMEWORK_DETECTION: frozenset(
        {
            ("classify_result",),
            ("complete_run",),
            ("execute_tests",),
        }
    ),
    DiagnosticRunStage.TEST_EXECUTION: frozenset({("parse_results",)}),
    DiagnosticRunStage.RESULT_PARSING: frozenset({("normalize_evidence",)}),
    DiagnosticRunStage.EVIDENCE_NORMALIZATION: frozenset({("classify_result",)}),
    DiagnosticRunStage.FAILURE_CLASSIFICATION: frozenset({("complete_run",)}),
}


class ForkCheckpointError(ValueError):
    """Indicate that a historical checkpoint cannot create a safe fork."""


def create_checkpoint_fork(
    graph: CompiledStateGraph,
    *,
    source_run_id: UUID,
    source_checkpoint_id: str,
    fork_run_id: UUID,
    repository_path: str | Path,
    test_execution_approved: bool = False,
) -> dict[str, dict[str, str]]:
    """Copy one safe historical state into a new run-scoped checkpoint thread."""
    if source_run_id == fork_run_id:
        raise ForkCheckpointError("A checkpoint fork requires a new diagnostic run ID.")
    if not source_checkpoint_id:
        raise ForkCheckpointError("A checkpoint fork requires a source checkpoint ID.")

    fork_config = build_checkpoint_config(fork_run_id)
    if graph.get_state(fork_config).values:
        raise ForkCheckpointError(
            f"Checkpoint history already exists for fork run ID {fork_run_id}."
        )

    source_config = build_checkpoint_config(
        source_run_id,
        checkpoint_id=source_checkpoint_id,
    )
    source_checkpoint = graph.get_state(source_config)
    _validate_source_checkpoint_identity(
        source_checkpoint,
        source_run_id=source_run_id,
        source_checkpoint_id=source_checkpoint_id,
    )

    source_state = source_checkpoint.values
    try:
        validate_resume_checkpoint(
            source_state,
            source_checkpoint.next,
            repository_path=repository_path,
            run_id=source_run_id,
            test_execution_approved=test_execution_approved,
        )
    except ResumeCheckpointError as error:
        message = str(error).replace("Resume may execute", "Fork may execute")
        raise ForkCheckpointError(message) from error

    source_run = source_state.get("run")
    if not isinstance(source_run, DiagnosticRun):
        raise ForkCheckpointError(
            "The source checkpoint must contain an initialized diagnostic run."
        )

    source_node = _get_source_node(source_run, source_checkpoint.next)
    forked_run = source_run.fork(
        run_id=fork_run_id,
        source_checkpoint_id=source_checkpoint_id,
        forked_at=datetime.now(UTC),
    )
    forked_state: AgentOpsState = {
        **source_state,
        "run_id": fork_run_id,
        "run": forked_run,
    }

    graph.update_state(
        fork_config,
        forked_state,
        as_node=source_node,
    )
    return fork_config


def _validate_source_checkpoint_identity(
    checkpoint: StateSnapshot,
    *,
    source_run_id: UUID,
    source_checkpoint_id: str,
) -> None:
    """Require the selected snapshot to belong to the requested source thread."""
    if not checkpoint.values:
        raise ForkCheckpointError(
            f"Checkpoint {source_checkpoint_id} was not found for run ID {source_run_id}."
        )

    configurable = checkpoint.config.get("configurable")
    if not isinstance(configurable, Mapping):
        raise ForkCheckpointError("The source checkpoint has invalid configuration.")
    if configurable.get("thread_id") != str(source_run_id):
        raise ForkCheckpointError("The source checkpoint belongs to a different diagnostic run.")
    if configurable.get("checkpoint_id") != source_checkpoint_id:
        raise ForkCheckpointError("The requested source checkpoint identity does not match.")


def _get_source_node(
    source_run: DiagnosticRun,
    next_nodes: tuple[str, ...],
) -> str:
    """Return the completed graph node represented by the selected checkpoint."""
    source_node = _SOURCE_NODE_BY_STAGE.get(source_run.stage)
    expected_next_nodes = _NEXT_NODES_BY_STAGE.get(source_run.stage)
    if source_node is None or expected_next_nodes is None:
        raise ForkCheckpointError(
            f"Checkpoint stage '{source_run.stage}' cannot create a diagnostic fork."
        )
    if next_nodes not in expected_next_nodes:
        node_names = ", ".join(next_nodes) or "none"
        raise ForkCheckpointError(
            f"The source checkpoint lifecycle does not match its pending operations: {node_names}."
        )

    return source_node
