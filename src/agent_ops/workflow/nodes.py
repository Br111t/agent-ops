"""Workflow nodes for the Agent-Ops diagnostic graph."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from agent_ops.analysis import (
    classify_failure,
    normalize_execution_evidence,
    parse_pytest_result,
)
from agent_ops.models import (
    DiagnosticRun,
    DiagnosticRunStage,
    FailureClassification,
    NormalizedExecutionEvidence,
    RepositoryProfile,
    TestExecutionResult,
    TestFrameworkProfile,
    TestResultSummary,
)
from agent_ops.repository import detect_test_framework, scan_repository
from agent_ops.tools import execute_approved_tests
from agent_ops.version import get_agent_ops_version
from agent_ops.workflow.state import AgentOpsState


def initialize_run_node(
    state: AgentOpsState,
) -> dict[str, UUID | DiagnosticRun]:
    """Create one stable run identity before diagnostic work begins."""
    run_id = state.get("run_id") or uuid4()
    started_at = utc_now()
    run = DiagnosticRun.start(
        run_id=run_id,
        target_repository=Path(state["repository_path"]).expanduser().resolve(),
        agent_ops_version=get_agent_ops_version(),
        started_at=started_at,
    )

    return {
        "run_id": run_id,
        "run": run,
    }


def inspect_repository_node(
    state: AgentOpsState,
) -> dict[str, RepositoryProfile | DiagnosticRun]:
    """Inspect the target repository and update its profile."""

    repository_profile = scan_repository(state["repository_path"])
    snapshot_sha256 = repository_profile.snapshot_sha256

    if snapshot_sha256 is None:
        raise ValueError("Repository inspection did not produce snapshot provenance.")

    recorded_at = utc_now()
    run = (
        state["run"]
        .record_repository_version(
            target_repository=repository_profile.root_path,
            snapshot_sha256=snapshot_sha256,
            git_commit_sha=repository_profile.git_commit_sha,
            recorded_at=recorded_at,
        )
        .transition(
            DiagnosticRunStage.REPOSITORY_INSPECTION,
            transitioned_at=recorded_at,
        )
    )

    return {
        "repository_profile": repository_profile,
        "run": run,
    }


def detect_framework_node(
    state: AgentOpsState,
) -> dict[str, TestFrameworkProfile | DiagnosticRun]:
    """Detect the test framework used by the target repository."""

    framework_profile = detect_test_framework(
        state["repository_path"],
    )

    return {
        "framework_profile": framework_profile,
        "run": _transition_run(state, DiagnosticRunStage.FRAMEWORK_DETECTION),
    }


def execute_tests_node(
    state: AgentOpsState,
) -> dict[str, TestExecutionResult | DiagnosticRun]:
    """Execute the detected and approved test command."""

    execution_result = execute_approved_tests(
        state["repository_path"],
        state["framework_profile"],
    )

    return {
        "execution_result": execution_result,
        "run": _transition_run(state, DiagnosticRunStage.TEST_EXECUTION),
    }


def parse_results_node(
    state: AgentOpsState,
) -> dict[str, TestResultSummary | DiagnosticRun]:
    """Parse structured evidence from the captured test result."""

    test_summary = parse_pytest_result(
        state["execution_result"],
    )

    return {
        "test_summary": test_summary,
        "run": _transition_run(state, DiagnosticRunStage.RESULT_PARSING),
    }


def normalize_evidence_node(
    state: AgentOpsState,
) -> dict[str, NormalizedExecutionEvidence | DiagnosticRun]:
    """Normalize execution metadata and parsed test evidence."""

    normalized_evidence = normalize_execution_evidence(
        state["execution_result"],
        state["test_summary"],
    )

    return {
        "normalized_evidence": normalized_evidence,
        "run": _transition_run(state, DiagnosticRunStage.EVIDENCE_NORMALIZATION),
    }


def classify_result_node(
    state: AgentOpsState,
) -> dict[str, FailureClassification | DiagnosticRun]:
    """Classify the diagnostic result using deterministic evidence."""

    classification = classify_failure(
        state["framework_profile"],
        state.get("normalized_evidence"),
    )

    return {
        "classification": classification,
        "run": _transition_run(state, DiagnosticRunStage.FAILURE_CLASSIFICATION),
    }


def complete_run_node(
    state: AgentOpsState,
) -> dict[str, DiagnosticRun]:
    """Mark a successfully traversed graph path as completed."""
    return {
        "run": state["run"].complete(completed_at=utc_now()),
    }


def utc_now() -> datetime:
    """Return one timezone-aware timestamp for lifecycle transitions."""
    return datetime.now(UTC)


def _transition_run(
    state: AgentOpsState,
    stage: DiagnosticRunStage,
) -> DiagnosticRun:
    """Advance run metadata after one node completes successfully."""
    return state["run"].transition(
        stage,
        transitioned_at=utc_now(),
    )
