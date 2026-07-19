"""Tests for safe local checkpoint configuration and connection lifetime."""

import os
import sqlite3
import stat
from pathlib import Path
from uuid import UUID

import pytest

from agent_ops.workflow import (
    build_checkpoint_config,
    get_default_checkpoint_database_path,
    open_sqlite_diagnostic_graph,
    resolve_checkpoint_database_path,
)

RUN_ID = "8ba9fe08-23c7-4eb0-8290-610dd0075e20"


def test_checkpoint_config_uses_run_id_as_thread_id() -> None:
    """Run and persistence identities should have one unambiguous mapping."""
    assert build_checkpoint_config(UUID(RUN_ID)) == {
        "configurable": {
            "thread_id": RUN_ID,
        }
    }


def test_default_checkpoint_path_honors_agent_ops_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The data directory override should produce a predictable database path."""
    data_directory = tmp_path / "agent-ops-data"
    monkeypatch.setenv("AGENT_OPS_HOME", str(data_directory))

    assert (
        get_default_checkpoint_database_path() == (data_directory / "checkpoints.sqlite3").resolve()
    )


def test_checkpoint_database_must_be_outside_target_repository(tmp_path: Path) -> None:
    """Persistence files must not alter or contaminate the inspected repository."""
    repository_path = tmp_path / "repository"
    repository_path.mkdir()

    with pytest.raises(ValueError, match="must be outside"):
        resolve_checkpoint_database_path(
            repository_path / ".agent-ops" / "checkpoints.sqlite3",
            repository_path=repository_path,
        )


def test_checkpoint_database_rejects_directory_path(tmp_path: Path) -> None:
    """A database path that names a directory should fail clearly."""
    repository_path = tmp_path / "repository"
    repository_path.mkdir()
    database_directory = tmp_path / "database-directory"
    database_directory.mkdir()

    with pytest.raises(IsADirectoryError, match="is a directory"):
        resolve_checkpoint_database_path(
            database_directory,
            repository_path=repository_path,
        )


def test_sqlite_graph_closes_connection_after_context(tmp_path: Path) -> None:
    """The graph context should create its database and release the connection."""
    repository_path = tmp_path / "repository"
    repository_path.mkdir()
    database_path = tmp_path / "state" / "checkpoints.sqlite3"

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=repository_path,
    ) as graph:
        connection = graph.checkpointer.conn
        assert database_path.exists()
        connection.execute("SELECT 1")

        if os.name != "nt":
            assert stat.S_IMODE(database_path.stat().st_mode) == 0o600
            assert stat.S_IMODE(database_path.parent.stat().st_mode) == 0o700

    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")
