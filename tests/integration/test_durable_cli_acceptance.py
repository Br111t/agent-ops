"""End-to-end acceptance coverage for durable diagnostic CLI runs."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

from agent_ops.models import DiagnosticRunStage, DiagnosticRunStatus
from agent_ops.workflow import build_checkpoint_config, open_sqlite_diagnostic_graph

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_REPOSITORY = PROJECT_ROOT / "examples" / "diagnostic-demo"
RUN_ID = UUID("5fbc62bc-05c1-4cec-920a-f9f29c332bc3")
RESUME_RUN_ID = UUID("1ccdcb0b-f47d-4522-b1a7-d26505b4d04e")


def _run_agent_ops(
    database_path: Path,
    *,
    run_id: UUID = RUN_ID,
    resume: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp1252"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("PYTHONUTF8", None)

    source_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        os.pathsep.join((source_path, existing_pythonpath)) if existing_pythonpath else source_path
    )

    command = [
        sys.executable,
        "-m",
        "agent_ops",
        str(DEMO_REPOSITORY),
        "--run-id",
        str(run_id),
        "--checkpoint-db",
        str(database_path),
    ]
    command.append("--resume" if resume else "--run-tests")

    return subprocess.run(
        command,
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


def test_real_cli_resumes_after_test_execution_without_replay(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "checkpoints.sqlite3"
    config = build_checkpoint_config(RESUME_RUN_ID)

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        stream = graph.stream(
            {
                "repository_path": str(DEMO_REPOSITORY),
                "run_tests": True,
                "run_id": RESUME_RUN_ID,
            },
            config,
            stream_mode="values",
        )
        for state in stream:
            run = state.get("run")
            if run is not None and run.stage is DiagnosticRunStage.TEST_EXECUTION:
                break
        stream.close()

        interrupted_state = graph.get_state(config)
        initial_history = list(graph.get_state_history(config))

    assert interrupted_state.values["run"].status is DiagnosticRunStatus.RUNNING
    assert interrupted_state.values["run"].stage is DiagnosticRunStage.TEST_EXECUTION
    assert interrupted_state.next == ("parse_results",)
    initial_execution = interrupted_state.values["execution_result"]
    initial_started_at = interrupted_state.values["run"].started_at
    initial_execution_checkpoints = _count_stage(
        initial_history,
        DiagnosticRunStage.TEST_EXECUTION,
    )
    assert initial_execution_checkpoints == 1

    resumed_run = _run_agent_ops(
        database_path,
        run_id=RESUME_RUN_ID,
        resume=True,
    )

    assert resumed_run.returncode == 0, resumed_run.stderr
    report = json.loads(resumed_run.stdout)
    assert report["run"]["run_id"] == str(RESUME_RUN_ID)
    assert report["run"]["status"] == "completed"
    assert datetime.fromisoformat(report["run"]["started_at"]) == initial_started_at
    assert report["test_execution"]["stdout"] == initial_execution.stdout
    assert report["test_execution"]["summary"]["passed"] == 5
    assert report["classification"]["category"] == "passed"

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        completed_state = graph.get_state(config)
        completed_history = list(graph.get_state_history(config))

    assert completed_state.values["run"].status is DiagnosticRunStatus.COMPLETED
    assert completed_state.next == ()
    assert len(completed_history) > len(initial_history)
    assert (
        _count_stage(completed_history, DiagnosticRunStage.TEST_EXECUTION)
        == initial_execution_checkpoints
    )

    completed_resume = _run_agent_ops(
        database_path,
        run_id=RESUME_RUN_ID,
        resume=True,
    )

    assert completed_resume.returncode == 2
    assert "diagnostic run is already completed" in completed_resume.stderr


def _count_stage(history: list[object], stage: DiagnosticRunStage) -> int:
    """Count checkpoints that persisted one lifecycle stage."""
    return sum(
        snapshot.values.get("run") is not None and snapshot.values["run"].stage is stage
        for snapshot in history
    )
