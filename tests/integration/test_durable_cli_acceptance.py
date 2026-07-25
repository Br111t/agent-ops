"""End-to-end acceptance coverage for durable diagnostic CLI runs."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

from agent_ops.models import DiagnosticRunStage, DiagnosticRunStatus
from agent_ops.workflow import (
    AgentOpsRuntimeContext,
    build_checkpoint_config,
    open_sqlite_diagnostic_graph,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_REPOSITORY = PROJECT_ROOT / "examples" / "diagnostic-demo"
RUN_ID = UUID("5fbc62bc-05c1-4cec-920a-f9f29c332bc3")
RESUME_RUN_ID = UUID("1ccdcb0b-f47d-4522-b1a7-d26505b4d04e")
REPLAY_RUN_ID = UUID("37986198-bcde-4313-b3bd-3252f768c43c")
FORK_SOURCE_RUN_ID = UUID("333eef53-e6f8-4084-8f8a-ea4a21f370d6")
FORK_RUN_ID = UUID("b7c0f75f-9270-4efe-9395-3dafb49d914b")
FORK_REPLAY_SOURCE_RUN_ID = UUID("242d9d33-c4e8-4fe3-a66d-820041bf2f05")
FORK_REPLAY_RUN_ID = UUID("18761eca-2e99-4dc8-80f3-ad3f3699e868")


def _run_agent_ops(
    database_path: Path,
    *,
    run_id: UUID = RUN_ID,
    resume: bool = False,
    history: bool = False,
    approve_test_replay: bool = False,
    fork_checkpoint_id: str | None = None,
    fork_run_id: UUID | None = None,
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
    if history:
        command.append("--history")
    elif fork_checkpoint_id is not None:
        command.extend(("--fork", "--checkpoint-id", fork_checkpoint_id))
        if fork_run_id is not None:
            command.extend(("--fork-run-id", str(fork_run_id)))
    else:
        command.append("--resume" if resume else "--run-tests")
    if approve_test_replay:
        command.append("--approve-test-replay")

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

    history_result = _run_agent_ops(database_path, history=True)

    assert history_result.returncode == 0, history_result.stderr
    history = json.loads(history_result.stdout)
    assert history["run_id"] == str(RUN_ID)
    assert history["checkpoint_count"] == len(initial_history)
    assert len(history["checkpoints"]) == len(initial_history)
    assert history["checkpoints"][0]["run_status"] == "completed"
    assert history["checkpoints"][0]["next_nodes"] == []
    assert history["checkpoints"][-1]["run_status"] is None

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
            context=AgentOpsRuntimeContext(test_execution_approved=True),
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


def test_real_cli_requires_renewed_approval_before_test_replay(tmp_path: Path) -> None:
    """A resumed invocation must not inherit stale test-execution approval."""
    database_path = tmp_path / "state" / "checkpoints.sqlite3"
    config = build_checkpoint_config(REPLAY_RUN_ID)

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        stream = graph.stream(
            {
                "repository_path": str(DEMO_REPOSITORY),
                "run_tests": True,
                "run_id": REPLAY_RUN_ID,
            },
            config,
            context=AgentOpsRuntimeContext(test_execution_approved=True),
            stream_mode="values",
        )
        for state in stream:
            run = state.get("run")
            if run is not None and run.stage is DiagnosticRunStage.FRAMEWORK_DETECTION:
                break
        stream.close()

        interrupted_state = graph.get_state(config)
        initial_history = list(graph.get_state_history(config))

    assert interrupted_state.values["run"].status is DiagnosticRunStatus.RUNNING
    assert interrupted_state.values["run"].stage is DiagnosticRunStage.FRAMEWORK_DETECTION
    assert interrupted_state.next == ("execute_tests",)
    assert "execution_result" not in interrupted_state.values

    rejected_resume = _run_agent_ops(
        database_path,
        run_id=REPLAY_RUN_ID,
        resume=True,
    )

    assert rejected_resume.returncode == 2
    assert "--approve-test-replay" in rejected_resume.stderr

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        assert len(list(graph.get_state_history(config))) == len(initial_history)

    approved_resume = _run_agent_ops(
        database_path,
        run_id=REPLAY_RUN_ID,
        resume=True,
        approve_test_replay=True,
    )

    assert approved_resume.returncode == 0, approved_resume.stderr
    report = json.loads(approved_resume.stdout)
    assert report["run"]["status"] == "completed"
    assert report["test_execution"]["summary"]["passed"] == 5

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        completed_history = list(graph.get_state_history(config))

    assert _count_stage(completed_history, DiagnosticRunStage.TEST_EXECUTION) == 1


def test_real_cli_forks_after_test_execution_without_replay(tmp_path: Path) -> None:
    """A post-execution fork should reuse evidence and preserve its source thread."""
    database_path = tmp_path / "state" / "checkpoints.sqlite3"
    source_config = build_checkpoint_config(FORK_SOURCE_RUN_ID)
    fork_config = build_checkpoint_config(FORK_RUN_ID)

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        stream = graph.stream(
            {
                "repository_path": str(DEMO_REPOSITORY),
                "run_tests": True,
                "run_id": FORK_SOURCE_RUN_ID,
            },
            source_config,
            context=AgentOpsRuntimeContext(test_execution_approved=True),
            stream_mode="values",
        )
        for state in stream:
            run = state.get("run")
            if run is not None and run.stage is DiagnosticRunStage.TEST_EXECUTION:
                break
        stream.close()

        source_checkpoint = graph.get_state(source_config)
        source_history_count = len(list(graph.get_state_history(source_config)))

    source_checkpoint_id = source_checkpoint.config["configurable"]["checkpoint_id"]
    forked_run = _run_agent_ops(
        database_path,
        run_id=FORK_SOURCE_RUN_ID,
        fork_checkpoint_id=source_checkpoint_id,
        fork_run_id=FORK_RUN_ID,
    )

    assert forked_run.returncode == 0, forked_run.stderr
    report = json.loads(forked_run.stdout)
    assert report["run"]["run_id"] == str(FORK_RUN_ID)
    assert report["run"]["status"] == "completed"
    assert report["run"]["forked_from"] == {
        "source_run_id": str(FORK_SOURCE_RUN_ID),
        "source_checkpoint_id": source_checkpoint_id,
    }
    assert report["test_execution"]["summary"]["passed"] == 5

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        preserved_source = graph.get_state(source_config)
        completed_fork = graph.get_state(fork_config)
        fork_history = list(graph.get_state_history(fork_config))

        assert len(list(graph.get_state_history(source_config))) == source_history_count

    assert preserved_source.values["run"].status is DiagnosticRunStatus.RUNNING
    assert preserved_source.values["run"].stage is DiagnosticRunStage.TEST_EXECUTION
    assert preserved_source.next == ("parse_results",)
    assert completed_fork.values["run"].status is DiagnosticRunStatus.COMPLETED
    assert fork_history[-1].metadata["source"] == "update"
    assert fork_history[-1].next == ("parse_results",)
    assert _count_stage(fork_history, DiagnosticRunStage.TEST_EXECUTION) == 1

    history_result = _run_agent_ops(
        database_path,
        run_id=FORK_RUN_ID,
        history=True,
    )
    assert history_result.returncode == 0, history_result.stderr
    history = json.loads(history_result.stdout)
    assert history["checkpoints"][0]["forked_from"]["source_run_id"] == str(FORK_SOURCE_RUN_ID)
    assert history["checkpoints"][0]["forked_from"]["source_checkpoint_id"] == (
        source_checkpoint_id
    )


def test_real_cli_requires_renewed_approval_for_forked_test_replay(
    tmp_path: Path,
) -> None:
    """A pre-execution fork must fail closed until replay is approved."""
    database_path = tmp_path / "state" / "checkpoints.sqlite3"
    source_config = build_checkpoint_config(FORK_REPLAY_SOURCE_RUN_ID)
    fork_config = build_checkpoint_config(FORK_REPLAY_RUN_ID)

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        stream = graph.stream(
            {
                "repository_path": str(DEMO_REPOSITORY),
                "run_tests": True,
                "run_id": FORK_REPLAY_SOURCE_RUN_ID,
            },
            source_config,
            context=AgentOpsRuntimeContext(test_execution_approved=True),
            stream_mode="values",
        )
        for state in stream:
            run = state.get("run")
            if run is not None and run.stage is DiagnosticRunStage.FRAMEWORK_DETECTION:
                break
        stream.close()

        source_checkpoint = graph.get_state(source_config)
        source_history_count = len(list(graph.get_state_history(source_config)))

    source_checkpoint_id = source_checkpoint.config["configurable"]["checkpoint_id"]
    rejected_fork = _run_agent_ops(
        database_path,
        run_id=FORK_REPLAY_SOURCE_RUN_ID,
        fork_checkpoint_id=source_checkpoint_id,
        fork_run_id=FORK_REPLAY_RUN_ID,
    )

    assert rejected_fork.returncode == 2
    assert "--approve-test-replay" in rejected_fork.stderr

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        assert graph.get_state(fork_config).values == {}
        assert len(list(graph.get_state_history(source_config))) == source_history_count

    approved_fork = _run_agent_ops(
        database_path,
        run_id=FORK_REPLAY_SOURCE_RUN_ID,
        fork_checkpoint_id=source_checkpoint_id,
        fork_run_id=FORK_REPLAY_RUN_ID,
        approve_test_replay=True,
    )

    assert approved_fork.returncode == 0, approved_fork.stderr
    report = json.loads(approved_fork.stdout)
    assert report["run"]["run_id"] == str(FORK_REPLAY_RUN_ID)
    assert report["run"]["status"] == "completed"
    assert report["run"]["forked_from"]["source_run_id"] == str(FORK_REPLAY_SOURCE_RUN_ID)
    assert report["test_execution"]["summary"]["passed"] == 5

    with open_sqlite_diagnostic_graph(
        database_path,
        repository_path=DEMO_REPOSITORY,
    ) as graph:
        completed_fork = graph.get_state(fork_config)
        fork_history = list(graph.get_state_history(fork_config))
        assert len(list(graph.get_state_history(source_config))) == source_history_count

    assert completed_fork.values["run"].status is DiagnosticRunStatus.COMPLETED
    assert _count_stage(fork_history, DiagnosticRunStage.TEST_EXECUTION) == 1


def _count_stage(history: list[object], stage: DiagnosticRunStage) -> int:
    """Count checkpoints that persisted one lifecycle stage."""
    return sum(
        snapshot.values.get("run") is not None and snapshot.values["run"].stage is stage
        for snapshot in history
    )
