"""Safety validation for resuming persisted diagnostic runs."""

from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from agent_ops.models import DiagnosticRunStatus
from agent_ops.repository import scan_repository
from agent_ops.workflow.state import AgentOpsState

SAFE_RESUME_NODES = frozenset(
    {
        "initialize_run",
        "inspect_repository",
        "detect_framework",
        "parse_results",
        "normalize_evidence",
        "classify_result",
        "complete_run",
    }
)
SIDE_EFFECTING_NODES = frozenset({"execute_tests"})
REQUIRED_STATE_FIELDS = {
    "initialize_run": frozenset({"repository_path", "run_id", "run_tests"}),
    "inspect_repository": frozenset({"repository_path", "run", "run_id", "run_tests"}),
    "detect_framework": frozenset({"repository_path", "repository_profile", "run"}),
    "parse_results": frozenset(
        {"execution_result", "framework_profile", "repository_profile", "run"}
    ),
    "normalize_evidence": frozenset(
        {
            "execution_result",
            "framework_profile",
            "repository_profile",
            "run",
            "test_summary",
        }
    ),
    "classify_result": frozenset({"framework_profile", "repository_profile", "run"}),
    "complete_run": frozenset({"framework_profile", "repository_profile", "run"}),
}


class ResumeCheckpointError(ValueError):
    """Indicate that a checkpoint cannot be resumed safely."""


def validate_resume_checkpoint(
    state: AgentOpsState,
    next_nodes: Sequence[str],
    *,
    repository_path: str | Path,
    run_id: UUID,
) -> None:
    """Validate identity, provenance, lifecycle, and the next operation."""
    if not state:
        raise ResumeCheckpointError(f"No checkpoint history exists for run ID {run_id}.")

    requested_repository = Path(repository_path).expanduser().resolve()
    saved_repository_value = state.get("repository_path")
    if not isinstance(saved_repository_value, (str, Path)):
        raise ResumeCheckpointError("The checkpoint does not contain a valid repository path.")

    saved_repository = Path(saved_repository_value).expanduser().resolve()
    if saved_repository != requested_repository:
        raise ResumeCheckpointError(
            f"The requested repository does not match the checkpoint repository: {saved_repository}"
        )

    saved_run_id = state.get("run_id")
    if saved_run_id is None:
        raise ResumeCheckpointError("The checkpoint does not contain a run identity.")
    if saved_run_id != run_id:
        raise ResumeCheckpointError("The checkpoint run identity does not match --run-id.")

    run = state.get("run")
    if run is not None:
        if run.run_id != run_id:
            raise ResumeCheckpointError("The persisted run identity does not match --run-id.")
        if run.provenance.target_repository != requested_repository:
            raise ResumeCheckpointError(
                "The persisted run provenance does not match the requested repository."
            )
        if run.status is DiagnosticRunStatus.COMPLETED:
            raise ResumeCheckpointError("The diagnostic run is already completed.")
        if run.status is not DiagnosticRunStatus.RUNNING:
            raise ResumeCheckpointError(
                f"A diagnostic run with status '{run.status}' cannot be resumed."
            )

    if not next_nodes:
        raise ResumeCheckpointError("The checkpoint has no pending operation to resume.")

    side_effecting_nodes = SIDE_EFFECTING_NODES.intersection(next_nodes)
    if side_effecting_nodes:
        node_names = ", ".join(sorted(side_effecting_nodes))
        raise ResumeCheckpointError(
            "Safe resume would replay a side-effecting operation "
            f"({node_names}); replay protection is not implemented yet."
        )

    unsupported_nodes = set(next_nodes).difference(SAFE_RESUME_NODES)
    if unsupported_nodes:
        node_names = ", ".join(sorted(unsupported_nodes))
        raise ResumeCheckpointError(
            f"The checkpoint contains unsupported pending operations: {node_names}."
        )

    required_fields = set().union(*(REQUIRED_STATE_FIELDS[node_name] for node_name in next_nodes))
    missing_fields = sorted(field_name for field_name in required_fields if field_name not in state)
    if missing_fields:
        field_names = ", ".join(missing_fields)
        raise ResumeCheckpointError(
            f"The checkpoint is missing state required to resume: {field_names}."
        )

    repository_profile = state.get("repository_profile")
    if repository_profile is None:
        return

    expected_snapshot = repository_profile.snapshot_sha256
    if expected_snapshot is None:
        raise ResumeCheckpointError(
            "The checkpoint does not contain repository snapshot provenance."
        )

    current_profile = scan_repository(requested_repository)
    if current_profile.snapshot_sha256 != expected_snapshot:
        raise ResumeCheckpointError(
            "The repository content has changed since the checkpoint was created."
        )
