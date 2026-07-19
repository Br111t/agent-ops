"""End-to-end acceptance coverage for durable diagnostic CLI runs."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

from agent_ops.models import DiagnosticRunStatus
from agent_ops.workflow import build_checkpoint_config, open_sqlite_diagnostic_graph

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_REPOSITORY = PROJECT_ROOT / "examples" / "diagnostic-demo"
RUN_ID = UUID("5fbc62bc-05c1-4cec-920a-f9f29c332bc3")


def _run_agent_ops(database_path: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp1252"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("PYTHONUTF8", None)

    source_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        os.pathsep.join((source_path, existing_pythonpath)) if existing_pythonpath else source_path
    )

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_ops",
            str(DEMO_REPOSITORY),
            "--run-tests",
            "--run-id",
            str(RUN_ID),
            "--checkpoint-db",
            str(database_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        text=True,
        timeout=30,
        check=False,
    )


def test_real_cli_persists_demo_run_and_rejects_duplicate(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "checkpoints.sqlite3"

    first_run = _run_agent_ops(database_path)

    assert first_run.returncode == 0, first_run.stderr
    report = json.loads(first_run.stdout)
    assert report["run"]["run_id"] == str(RUN_ID)
    assert report["run"]["status"] == "completed"
    assert report["repository"]["snapshot_sha256"]
    assert report["test_framework"]["framework"] == "pytest"
    assert report["test_execution"]["exit_code"] == 0
    assert report["test_execution"]["succeeded"] is True
    assert report["test_execution"]["summary"]["passed"] == 5
    assert report["test_execution"]["summary"]["total_tests"] == 5
    assert "✅ total: $3.75 → ready" in report["test_execution"]["stdout"]
    assert report["classification"]["category"] == "passed"
    assert database_path.is_file()

    config = build_checkpoint_config(RUN_ID)
    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        persisted_state = graph.get_state(config)
        initial_history = list(graph.get_state_history(config))

    assert persisted_state.values["run"].status is DiagnosticRunStatus.COMPLETED
    assert persisted_state.next == ()
    assert len(initial_history) >= 5

    duplicate_run = _run_agent_ops(database_path)

    assert duplicate_run.returncode == 2
    assert duplicate_run.stdout == ""
    assert "Checkpoint history already exists for this run ID" in duplicate_run.stderr

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        duplicate_history = list(graph.get_state_history(config))

    assert len(duplicate_history) == len(initial_history)
