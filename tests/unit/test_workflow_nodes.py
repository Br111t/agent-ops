"""Tests for Agent-Ops workflow nodes."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from agent_ops.models import (
    DiagnosticRun,
    DiagnosticRunStage,
    DiagnosticRunStatus,
    FailureCategory,
    FailureClassification,
    RepositoryProfile,
)
from agent_ops.models import (
    NormalizedExecutionEvidence as ExecutionEvidence,
)
from agent_ops.models import (
    TestExecutionResult as ExecutionResult,
)
from agent_ops.models import (
    TestFramework as Framework,
)
from agent_ops.models import (
    TestFrameworkProfile as FrameworkProfile,
)
from agent_ops.models import (
    TestResultSummary as ResultSummary,
)
from agent_ops.workflow.nodes import (
    classify_result_node,
    complete_run_node,
    detect_framework_node,
    execute_tests_node,
    initialize_run_node,
    inspect_repository_node,
    normalize_evidence_node,
    parse_results_node,
)

RUN_ID = UUID("8ba9fe08-23c7-4eb0-8290-610dd0075e20")
STARTED_AT = datetime(2000, 1, 1, tzinfo=UTC)
SNAPSHOT_SHA256 = "a" * 64


def test_initialize_run_node_preserves_supplied_identity() -> None:
    """Initialization should accept an externally assigned stable run ID."""
    with (
        patch("agent_ops.workflow.nodes.utc_now", return_value=STARTED_AT),
        patch(
            "agent_ops.workflow.nodes.get_agent_ops_version",
            return_value="0.1.0",
        ),
    ):
        result = initialize_run_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": False,
                "run_id": RUN_ID,
            }
        )

    assert result["run_id"] == RUN_ID
    assert result["run"].run_id == RUN_ID
    assert result["run"].status is DiagnosticRunStatus.RUNNING
    assert result["run"].stage is DiagnosticRunStage.INITIALIZED
    assert result["run"].provenance.agent_ops_version == "0.1.0"


def test_inspect_repository_node_returns_profile() -> None:
    """Repository inspection should return a partial state update."""

    expected = RepositoryProfile(
        root_path=Path("/tmp/example"),
        repository_name="example",
        file_count=3,
        detected_languages=["Python"],
        configuration_files=["pyproject.toml"],
        test_files=["tests/test_example.py"],
        has_git_directory=True,
        git_commit_sha="b" * 40,
        snapshot_sha256=SNAPSHOT_SHA256,
    )

    with patch(
        "agent_ops.workflow.nodes.scan_repository",
        return_value=expected,
    ) as scan_repository:
        result = inspect_repository_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": False,
                "run": _run_at(DiagnosticRunStage.INITIALIZED, with_provenance=False),
            }
        )

    assert result["repository_profile"] == expected
    assert result["run"].stage is DiagnosticRunStage.REPOSITORY_INSPECTION
    assert result["run"].provenance.target_repository_version == (f"sha256:{SNAPSHOT_SHA256}")
    assert result["run"].provenance.target_repository_revision == "b" * 40
    scan_repository.assert_called_once_with("/tmp/example")


def test_detect_framework_node_returns_profile() -> None:
    """Framework detection should return a partial state update."""

    expected = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        evidence=["pyproject.toml configures pytest"],
        approved_command=("python", "-m", "pytest", "-q"),
    )

    with patch(
        "agent_ops.workflow.nodes.detect_test_framework",
        return_value=expected,
    ) as detect_test_framework:
        result = detect_framework_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": False,
                "run": _run_at(DiagnosticRunStage.REPOSITORY_INSPECTION),
            }
        )

    assert result["framework_profile"] == expected
    assert result["run"].stage is DiagnosticRunStage.FRAMEWORK_DETECTION
    detect_test_framework.assert_called_once_with("/tmp/example")


def test_execute_tests_node_returns_execution_result() -> None:
    """Approved execution should return captured test evidence."""

    framework_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        approved_command=("python", "-m", "pytest", "-q"),
    )
    expected = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="2 passed in 0.10s\n",
        stderr="",
        duration_seconds=0.1,
        timed_out=False,
    )

    with patch(
        "agent_ops.workflow.nodes.execute_approved_tests",
        return_value=expected,
    ) as execute_approved_tests:
        result = execute_tests_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": True,
                "framework_profile": framework_profile,
                "run": _run_at(DiagnosticRunStage.FRAMEWORK_DETECTION),
            }
        )

    assert result["execution_result"] == expected
    assert result["run"].stage is DiagnosticRunStage.TEST_EXECUTION
    execute_approved_tests.assert_called_once_with(
        "/tmp/example",
        framework_profile,
    )


def test_parse_results_node_returns_summary() -> None:
    """Captured output should be converted into structured evidence."""

    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="2 passed in 0.10s\n",
        stderr="",
        duration_seconds=0.1,
        timed_out=False,
    )
    expected = ResultSummary(
        summary_found=True,
        summary_line="2 passed in 0.10s",
        passed=2,
    )

    with patch(
        "agent_ops.workflow.nodes.parse_pytest_result",
        return_value=expected,
    ) as parse_pytest_result:
        result = parse_results_node(
            {
                "repository_path": "/tmp/example",
                "run_tests": True,
                "execution_result": execution_result,
                "run": _run_at(DiagnosticRunStage.TEST_EXECUTION),
            }
        )

    assert result["test_summary"] == expected
    assert result["run"].stage is DiagnosticRunStage.RESULT_PARSING
    parse_pytest_result.assert_called_once_with(execution_result)


def test_normalize_evidence_node_combines_execution_evidence() -> None:
    """The normalization node should return consistent execution evidence."""

    execution_result = ExecutionResult(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        stdout="1 failed in 0.20s\n",
        stderr="",
        duration_seconds=0.3,
        timed_out=False,
    )
    test_summary = ResultSummary(
        summary_found=True,
        summary_line="1 failed in 0.20s",
        failed=1,
    )
    normalized_evidence = ExecutionEvidence(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        timed_out=False,
        duration_seconds=0.3,
        summary_found=True,
        summary_line="1 failed in 0.20s",
        failed=1,
    )

    with patch(
        "agent_ops.workflow.nodes.normalize_execution_evidence",
        return_value=normalized_evidence,
    ) as normalize:
        result = normalize_evidence_node(
            {
                "repository_path": ".",
                "run_tests": True,
                "execution_result": execution_result,
                "test_summary": test_summary,
                "run": _run_at(DiagnosticRunStage.RESULT_PARSING),
            }
        )

    assert result["normalized_evidence"] == normalized_evidence
    assert result["run"].stage is DiagnosticRunStage.EVIDENCE_NORMALIZATION
    normalize.assert_called_once_with(
        execution_result,
        test_summary,
    )


def test_classify_result_node_returns_classification() -> None:
    """Normalized evidence should produce a deterministic classification."""

    framework_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=1.0,
        approved_command=("python", "-m", "pytest", "-q"),
    )
    normalized_evidence = ExecutionEvidence(
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        timed_out=False,
        duration_seconds=0.3,
        summary_found=True,
        summary_line="1 failed in 0.20s",
        failed=1,
    )
    expected = FailureClassification(
        category=FailureCategory.TEST_FAILURE,
        confidence=0.99,
        evidence=("Parsed output reported 1 failed test(s).",),
        recommended_next_step=("Inspect assertion messages and affected test cases."),
    )

    with patch(
        "agent_ops.workflow.nodes.classify_failure",
        return_value=expected,
    ) as classify:
        result = classify_result_node(
            {
                "repository_path": ".",
                "run_tests": True,
                "framework_profile": framework_profile,
                "normalized_evidence": normalized_evidence,
                "run": _run_at(DiagnosticRunStage.EVIDENCE_NORMALIZATION),
            }
        )

    assert result["classification"] == expected
    assert result["run"].stage is DiagnosticRunStage.FAILURE_CLASSIFICATION
    classify.assert_called_once_with(
        framework_profile,
        normalized_evidence,
    )


def test_complete_run_node_marks_lifecycle_terminal() -> None:
    """The terminal graph node should complete a fully identified run."""
    result = complete_run_node(
        {
            "repository_path": "/tmp/example",
            "run_tests": False,
            "run": _run_at(DiagnosticRunStage.FRAMEWORK_DETECTION),
        }
    )

    assert result["run"].status is DiagnosticRunStatus.COMPLETED
    assert result["run"].stage is DiagnosticRunStage.COMPLETED
    assert result["run"].finished_at is not None


def _run_at(
    stage: DiagnosticRunStage,
    *,
    with_provenance: bool = True,
) -> DiagnosticRun:
    """Return a valid running run positioned at a requested test stage."""
    run = DiagnosticRun.start(
        run_id=RUN_ID,
        target_repository=Path("/tmp/example"),
        agent_ops_version="0.1.0",
        started_at=STARTED_AT,
    )

    if with_provenance:
        run = run.record_repository_version(
            target_repository=Path("/tmp/example"),
            snapshot_sha256=SNAPSHOT_SHA256,
            git_commit_sha=None,
            recorded_at=STARTED_AT,
        )

    if stage is not DiagnosticRunStage.INITIALIZED:
        run = run.transition(stage, transitioned_at=STARTED_AT)

    return run
