"""Models describing one durable diagnostic-run identity and lifecycle."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DiagnosticRunStatus(StrEnum):
    """Lifecycle states for one diagnostic run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class DiagnosticRunStage(StrEnum):
    """Ordered stages supported by the current diagnostic workflow."""

    INITIALIZED = "initialized"
    REPOSITORY_INSPECTION = "repository_inspection"
    FRAMEWORK_DETECTION = "framework_detection"
    TEST_EXECUTION = "test_execution"
    RESULT_PARSING = "result_parsing"
    EVIDENCE_NORMALIZATION = "evidence_normalization"
    FAILURE_CLASSIFICATION = "failure_classification"
    COMPLETED = "completed"


_STAGE_ORDER = {stage: index for index, stage in enumerate(DiagnosticRunStage)}


class DiagnosticRunProvenance(BaseModel):
    """Versions required to interpret or reproduce a diagnostic run."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    agent_ops_version: str = Field(min_length=1)
    target_repository: Path
    target_repository_version: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    target_repository_revision: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40}$",
    )


class DiagnosticRun(BaseModel):
    """Immutable identity, lifecycle, and provenance for one diagnostic run."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    run_id: UUID
    status: DiagnosticRunStatus
    stage: DiagnosticRunStage
    started_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    provenance: DiagnosticRunProvenance

    @field_validator("started_at", "updated_at", "finished_at")
    @classmethod
    def validate_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require unambiguous timestamps suitable for persistence."""
        if value is not None and value.tzinfo is None:
            raise ValueError("Diagnostic run timestamps must include a timezone.")

        return value

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "DiagnosticRun":
        """Require chronological timestamps and consistent terminal state."""
        if self.updated_at < self.started_at:
            raise ValueError("updated_at cannot precede started_at.")

        if self.finished_at is not None and self.finished_at < self.updated_at:
            raise ValueError("finished_at cannot precede updated_at.")

        if (
            self.stage is DiagnosticRunStage.COMPLETED
            and self.status is not DiagnosticRunStatus.COMPLETED
        ):
            raise ValueError("Only a completed diagnostic run may use the completed stage.")

        if self.status is DiagnosticRunStatus.RUNNING:
            if self.finished_at is not None:
                raise ValueError("A running diagnostic run cannot have finished_at.")
            if self.stage is DiagnosticRunStage.COMPLETED:
                raise ValueError("A running diagnostic run cannot use the completed stage.")
        elif self.finished_at is None:
            raise ValueError("A terminal diagnostic run requires finished_at.")

        if self.status is DiagnosticRunStatus.COMPLETED:
            if self.stage is not DiagnosticRunStage.COMPLETED:
                raise ValueError("A completed diagnostic run requires the completed stage.")
            if self.provenance.target_repository_version is None:
                raise ValueError(
                    "A completed diagnostic run requires target repository provenance."
                )

        return self

    @classmethod
    def start(
        cls,
        *,
        run_id: UUID,
        target_repository: Path,
        agent_ops_version: str,
        started_at: datetime,
    ) -> "DiagnosticRun":
        """Create a running diagnostic run before repository inspection."""
        return cls(
            run_id=run_id,
            status=DiagnosticRunStatus.RUNNING,
            stage=DiagnosticRunStage.INITIALIZED,
            started_at=started_at,
            updated_at=started_at,
            provenance=DiagnosticRunProvenance(
                agent_ops_version=agent_ops_version,
                target_repository=target_repository,
            ),
        )

    def transition(
        self,
        stage: DiagnosticRunStage,
        *,
        transitioned_at: datetime,
    ) -> "DiagnosticRun":
        """Advance a running diagnostic run to the same or a later stage."""
        if self.status is not DiagnosticRunStatus.RUNNING:
            raise ValueError("Only a running diagnostic run can transition stages.")

        if stage is DiagnosticRunStage.COMPLETED:
            raise ValueError("Use complete() to enter the completed stage.")

        if _STAGE_ORDER[stage] < _STAGE_ORDER[self.stage]:
            raise ValueError("Diagnostic run stages cannot move backward.")

        if transitioned_at < self.updated_at:
            raise ValueError("A lifecycle transition cannot move time backward.")

        return type(self).model_validate(
            {
                **self.model_dump(),
                "stage": stage,
                "updated_at": transitioned_at,
            }
        )

    def record_repository_version(
        self,
        *,
        target_repository: Path,
        snapshot_sha256: str,
        git_commit_sha: str | None,
        recorded_at: datetime,
    ) -> "DiagnosticRun":
        """Attach the inspected repository snapshot to this run's provenance."""
        if self.status is not DiagnosticRunStatus.RUNNING:
            raise ValueError("Repository provenance can be recorded only while running.")

        if recorded_at < self.updated_at:
            raise ValueError("Repository provenance cannot move time backward.")

        provenance = DiagnosticRunProvenance.model_validate(
            {
                **self.provenance.model_dump(),
                "target_repository": target_repository,
                "target_repository_version": f"sha256:{snapshot_sha256}",
                "target_repository_revision": git_commit_sha,
            }
        )

        return type(self).model_validate(
            {
                **self.model_dump(),
                "updated_at": recorded_at,
                "provenance": provenance,
            }
        )

    def complete(self, *, completed_at: datetime) -> "DiagnosticRun":
        """Finish a successfully completed diagnostic run."""
        if self.status is not DiagnosticRunStatus.RUNNING:
            raise ValueError("Only a running diagnostic run can complete.")

        if completed_at < self.updated_at:
            raise ValueError("Completion cannot move time backward.")

        return type(self).model_validate(
            {
                **self.model_dump(),
                "status": DiagnosticRunStatus.COMPLETED,
                "stage": DiagnosticRunStage.COMPLETED,
                "updated_at": completed_at,
                "finished_at": completed_at,
            }
        )
