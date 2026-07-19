"""Integration tests for persisted diagnostic graph checkpoints."""

from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest

from agent_ops.models import (
    DiagnosticRunStatus,
    RepositoryProfile,
)
from agent_ops.models import TestFramework as Framework
from agent_ops.models import TestFrameworkProfile as FrameworkProfile
from agent_ops.workflow import open_sqlite_diagnostic_graph

RUN_ID = UUID("8ba9fe08-23c7-4eb0-8290-610dd0075e20")


def test_sqlite_checkpoints_survive_graph_reopen(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Completed state and checkpoint history should survive connection closure."""
    repository_path = tmp_path / "repository"
    repository_path.mkdir()
    database_path = tmp_path / "state" / "checkpoints.sqlite3"
    repository_profile = RepositoryProfile(
        root_path=repository_path,
        repository_name="repository",
        file_count=1,
        detected_languages=["Python"],
        configuration_files=["pyproject.toml"],
        test_files=["tests/test_example.py"],
        has_git_directory=True,
        git_commit_sha="b" * 40,
        snapshot_sha256="a" * 64,
    )
    framework_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        approved_command=("python", "-m", "pytest", "-q"),
    )
    config = {
        "configurable": {
            "thread_id": str(RUN_ID),
        }
    }

    with (
        patch(
            "agent_ops.workflow.nodes.scan_repository",
            return_value=repository_profile,
        ),
        patch(
            "agent_ops.workflow.nodes.detect_test_framework",
            return_value=framework_profile,
        ),
        open_sqlite_diagnostic_graph(
            database_path,
            repository_path=repository_path,
        ) as graph,
    ):
        result = graph.invoke(
            {
                "repository_path": str(repository_path),
                "run_tests": False,
                "run_id": RUN_ID,
            },
            config,
        )
        initial_history = list(graph.get_state_history(config))

    assert result["run"].status is DiagnosticRunStatus.COMPLETED
    assert len(initial_history) >= 5

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=repository_path,
    ) as reopened_graph:
        persisted_state = reopened_graph.get_state(config)
        reopened_history = list(reopened_graph.get_state_history(config))

    assert persisted_state.values["run"].status is DiagnosticRunStatus.COMPLETED
    assert persisted_state.values["run_id"] == RUN_ID
    assert persisted_state.next == ()
    assert len(reopened_history) == len(initial_history)
    assert "unregistered type" not in caplog.text
