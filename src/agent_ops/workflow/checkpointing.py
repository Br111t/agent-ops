"""SQLite checkpoint lifecycle for local Agent-Ops diagnostic runs."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from agent_ops.config import get_agent_ops_data_directory
from agent_ops.models import (
    DiagnosticRun,
    DiagnosticRunProvenance,
    DiagnosticRunStage,
    DiagnosticRunStatus,
    FailureCategory,
    FailureClassification,
    NormalizedExecutionEvidence,
    RepositoryProfile,
    TestExecutionResult,
    TestFramework,
    TestFrameworkProfile,
    TestResultSummary,
)
from agent_ops.workflow.graph import build_diagnostic_graph

DEFAULT_CHECKPOINT_DATABASE_FILENAME = "checkpoints.sqlite3"
TRUSTED_CHECKPOINT_TYPES: tuple[type, ...] = (
    DiagnosticRun,
    DiagnosticRunProvenance,
    DiagnosticRunStage,
    DiagnosticRunStatus,
    FailureCategory,
    FailureClassification,
    NormalizedExecutionEvidence,
    RepositoryProfile,
    TestExecutionResult,
    TestFramework,
    TestFrameworkProfile,
    TestResultSummary,
)


def build_checkpoint_config(run_id: UUID) -> dict[str, dict[str, str]]:
    """Use the stable diagnostic run UUID as its LangGraph thread identity."""
    return {
        "configurable": {
            "thread_id": str(run_id),
        }
    }


def get_default_checkpoint_database_path() -> Path:
    """Return the default durable checkpoint database path."""
    return get_agent_ops_data_directory() / DEFAULT_CHECKPOINT_DATABASE_FILENAME


def resolve_checkpoint_database_path(
    checkpoint_path: str | Path | None,
    *,
    repository_path: str | Path,
) -> Path:
    """Resolve a checkpoint path that cannot modify the inspected repository."""
    database_path = (
        Path(checkpoint_path or get_default_checkpoint_database_path()).expanduser().resolve()
    )
    target_repository = Path(repository_path).expanduser().resolve()

    if database_path == target_repository or database_path.is_relative_to(target_repository):
        raise ValueError("The checkpoint database must be outside the repository being inspected.")

    if database_path.exists() and database_path.is_dir():
        raise IsADirectoryError(f"Checkpoint database path is a directory: {database_path}")

    return database_path


@contextmanager
def open_sqlite_diagnostic_graph(
    checkpoint_path: str | Path | None,
    *,
    repository_path: str | Path,
) -> Iterator[CompiledStateGraph]:
    """Open a compiled diagnostic graph and close its SQLite connection safely."""
    database_path = resolve_checkpoint_database_path(
        checkpoint_path,
        repository_path=repository_path,
    )
    database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path, check_same_thread=False)
    try:
        if os.name != "nt":
            database_path.chmod(0o600)

        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=TRUSTED_CHECKPOINT_TYPES,
        )
        checkpointer = SqliteSaver(connection, serde=serializer)
        yield build_diagnostic_graph(checkpointer=checkpointer)
    finally:
        connection.close()
