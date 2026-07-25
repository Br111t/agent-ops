"""Tests for safe diagnostic checkpoint forks."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest
from langgraph.types import StateSnapshot

from agent_ops.models import (
    DiagnosticRun,
    DiagnosticRunStage,
)
from agent_ops.models import TestExecutionResult as ExecutionResult
from agent_ops.models import TestFramework as Framework
from agent_ops.models import TestFrameworkProfile as FrameworkProfile
from agent_ops.repository import scan_repository
from agent_ops.workflow import ForkCheckpointError, create_checkpoint_fork
from agent_ops.workflow.state import AgentOpsState

SOURCE_RUN_ID = UUID("8ba9fe08-23c7-4eb0-8290-610dd0075e20")
FORK_RUN_ID = UUID("00918f6e-57ad-49fe-8e85-51801ac11a85")
CHECKPOINT_ID = "checkpoint-source"
STARTED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def test_fork_copies_historical_state_into_new_run(tmp_path: Path) -> None:
    """A fork should preserve evidence while replacing run identity and lineage."""
    state = _forkable_state(tmp_path, stage=DiagnosticRunStage.TEST_EXECUTION)
    source_snapshot = _snapshot(state, next_nodes=("parse_results",))
    graph = Mock()
    graph.get_state.side_effect = [
        _snapshot({}, run_id=FORK_RUN_ID),
        source_snapshot,
    ]

    config = create_checkpoint_fork(
        graph,
        source_run_id=SOURCE_RUN_ID,
        source_checkpoint_id=CHECKPOINT_ID,
        fork_run_id=FORK_RUN_ID,
        repository_path=state["repository_path"],
    )

    assert config == _config(FORK_RUN_ID)
    graph.update_state.assert_called_once()
    update_config, forked_state = graph.update_state.call_args.args
    assert update_config == _config(FORK_RUN_ID)
    assert graph.update_state.call_args.kwargs == {"as_node": "execute_tests"}
    assert forked_state["run_id"] == FORK_RUN_ID
    assert forked_state["execution_result"] == state["execution_result"]
    assert forked_state["run"].run_id == FORK_RUN_ID
    assert forked_state["run"].stage is DiagnosticRunStage.TEST_EXECUTION
    assert forked_state["run"].forked_from is not None
    assert forked_state["run"].forked_from.source_run_id == SOURCE_RUN_ID
    assert forked_state["run"].forked_from.source_checkpoint_id == CHECKPOINT_ID
    assert state["run_id"] == SOURCE_RUN_ID
    assert state["run"].forked_from is None


def test_fork_requires_renewed_approval_before_test_execution(tmp_path: Path) -> None:
    """Selecting a pre-execution checkpoint must not inherit saved test intent."""
    state = _forkable_state(tmp_path, stage=DiagnosticRunStage.FRAMEWORK_DETECTION)
    source_snapshot = _snapshot(state, next_nodes=("execute_tests",))
    graph = Mock()
    graph.get_state.side_effect = [
        _snapshot({}, run_id=FORK_RUN_ID),
        source_snapshot,
    ]

    with pytest.raises(ForkCheckpointError, match="Fork may execute.*approve-test-replay"):
        create_checkpoint_fork(
            graph,
            source_run_id=SOURCE_RUN_ID,
            source_checkpoint_id=CHECKPOINT_ID,
            fork_run_id=FORK_RUN_ID,
            repository_path=state["repository_path"],
        )

    graph.update_state.assert_not_called()


def test_fork_accepts_renewed_approval_before_test_execution(tmp_path: Path) -> None:
    """Fresh approval may authorize the forked invocation's test execution."""
    state = _forkable_state(tmp_path, stage=DiagnosticRunStage.FRAMEWORK_DETECTION)
    source_snapshot = _snapshot(state, next_nodes=("execute_tests",))
    graph = Mock()
    graph.get_state.side_effect = [
        _snapshot({}, run_id=FORK_RUN_ID),
        source_snapshot,
    ]

    create_checkpoint_fork(
        graph,
        source_run_id=SOURCE_RUN_ID,
        source_checkpoint_id=CHECKPOINT_ID,
        fork_run_id=FORK_RUN_ID,
        repository_path=state["repository_path"],
        test_execution_approved=True,
    )

    assert graph.update_state.call_args.kwargs == {"as_node": "detect_framework"}


def test_fork_rejects_existing_target_run(tmp_path: Path) -> None:
    """Fork creation must not overwrite another run's checkpoint thread."""
    graph = Mock()
    graph.get_state.return_value = _snapshot(
        {"run_id": FORK_RUN_ID},
        run_id=FORK_RUN_ID,
    )

    with pytest.raises(ForkCheckpointError, match="already exists for fork run ID"):
        create_checkpoint_fork(
            graph,
            source_run_id=SOURCE_RUN_ID,
            source_checkpoint_id=CHECKPOINT_ID,
            fork_run_id=FORK_RUN_ID,
            repository_path=tmp_path,
        )

    assert graph.get_state.call_count == 1
    graph.update_state.assert_not_called()


def test_fork_rejects_missing_source_checkpoint(tmp_path: Path) -> None:
    """An unknown checkpoint ID cannot silently fall back to the latest state."""
    graph = Mock()
    graph.get_state.side_effect = [
        _snapshot({}, run_id=FORK_RUN_ID),
        _snapshot({}),
    ]

    with pytest.raises(ForkCheckpointError, match="was not found"):
        create_checkpoint_fork(
            graph,
            source_run_id=SOURCE_RUN_ID,
            source_checkpoint_id=CHECKPOINT_ID,
            fork_run_id=FORK_RUN_ID,
            repository_path=tmp_path,
        )

    graph.update_state.assert_not_called()


def test_fork_rejects_same_source_and_target_run(tmp_path: Path) -> None:
    """A fork must use a separate thread so its source history remains immutable."""
    graph = Mock()

    with pytest.raises(ForkCheckpointError, match="requires a new diagnostic run ID"):
        create_checkpoint_fork(
            graph,
            source_run_id=SOURCE_RUN_ID,
            source_checkpoint_id=CHECKPOINT_ID,
            fork_run_id=SOURCE_RUN_ID,
            repository_path=tmp_path,
        )

    graph.get_state.assert_not_called()


def test_fork_rejects_inconsistent_lifecycle_and_pending_node(tmp_path: Path) -> None:
    """The selected lifecycle stage must identify the node that produced it."""
    state = _forkable_state(tmp_path, stage=DiagnosticRunStage.TEST_EXECUTION)
    graph = Mock()
    graph.get_state.side_effect = [
        _snapshot({}, run_id=FORK_RUN_ID),
        _snapshot(state, next_nodes=("complete_run",)),
    ]

    with pytest.raises(ForkCheckpointError, match="lifecycle does not match"):
        create_checkpoint_fork(
            graph,
            source_run_id=SOURCE_RUN_ID,
            source_checkpoint_id=CHECKPOINT_ID,
            fork_run_id=FORK_RUN_ID,
            repository_path=state["repository_path"],
        )

    graph.update_state.assert_not_called()


def _forkable_state(
    tmp_path: Path,
    *,
    stage: DiagnosticRunStage,
) -> AgentOpsState:
    """Build checkpoint state with real repository provenance."""
    repository_path = tmp_path / "repository"
    repository_path.mkdir()
    (repository_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    repository_profile = scan_repository(repository_path)
    snapshot_sha256 = repository_profile.snapshot_sha256
    assert snapshot_sha256 is not None

    run = DiagnosticRun.start(
        run_id=SOURCE_RUN_ID,
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
        stage,
        transitioned_at=STARTED_AT + timedelta(seconds=2),
    )

    state: AgentOpsState = {
        "repository_path": str(repository_path),
        "run_tests": True,
        "run_id": SOURCE_RUN_ID,
        "run": run,
        "repository_profile": repository_profile,
        "framework_profile": FrameworkProfile(
            framework=Framework.PYTEST,
            confidence=1.0,
            approved_command=("python", "-m", "pytest", "-q"),
        ),
    }
    if stage is DiagnosticRunStage.TEST_EXECUTION:
        state["execution_result"] = ExecutionResult(
            command=("python", "-m", "pytest", "-q"),
            exit_code=0,
            stdout="1 passed in 0.01s\n",
            duration_seconds=0.01,
        )

    return state


def _snapshot(
    values: dict[str, object] | AgentOpsState,
    *,
    run_id: UUID = SOURCE_RUN_ID,
    next_nodes: tuple[str, ...] = (),
) -> StateSnapshot:
    """Build one checkpoint snapshot returned by a compiled graph."""
    return StateSnapshot(
        values=values,
        next=next_nodes,
        config=_config(run_id, checkpoint_id=CHECKPOINT_ID),
        metadata={"source": "loop", "step": 3, "parents": {}},
        created_at=STARTED_AT.isoformat(),
        parent_config=None,
        tasks=(),
        interrupts=(),
    )


def _config(
    run_id: UUID,
    *,
    checkpoint_id: str | None = None,
) -> dict[str, dict[str, str]]:
    """Return a thread or checkpoint-specific graph configuration."""
    configurable = {"thread_id": str(run_id)}
    if checkpoint_id is not None:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}
