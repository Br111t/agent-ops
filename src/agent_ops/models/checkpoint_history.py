"""Public models for retained diagnostic checkpoint history."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from agent_ops.models.diagnostic_run import DiagnosticRunStage, DiagnosticRunStatus


class DiagnosticCheckpointSource(StrEnum):
    """Supported causes of a persisted workflow checkpoint."""

    INPUT = "input"
    LOOP = "loop"
    UPDATE = "update"
    FORK = "fork"


class DiagnosticCheckpointRecord(BaseModel):
    """Stable, serializable summary of one persisted graph checkpoint."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    run_id: UUID
    checkpoint_id: str = Field(min_length=1)
    parent_checkpoint_id: str | None = Field(default=None, min_length=1)
    step: int = Field(ge=-1)
    source: DiagnosticCheckpointSource
    created_at: datetime
    run_status: DiagnosticRunStatus | None = None
    run_stage: DiagnosticRunStage | None = None
    next_nodes: tuple[str, ...] = ()

    @field_validator("created_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Require an unambiguous persisted checkpoint timestamp."""
        if value.tzinfo is None:
            raise ValueError("Checkpoint timestamps must include a timezone.")

        return value

    @model_validator(mode="after")
    def validate_run_lifecycle_pair(self) -> "DiagnosticCheckpointRecord":
        """Require status and stage to come from the same persisted run state."""
        if (self.run_status is None) != (self.run_stage is None):
            raise ValueError("Checkpoint run status and stage must be present together.")

        return self


class DiagnosticCheckpointHistory(BaseModel):
    """Newest-first retained checkpoints for one diagnostic run."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    run_id: UUID
    checkpoints: tuple[DiagnosticCheckpointRecord, ...] = ()

    @computed_field
    @property
    def checkpoint_count(self) -> int:
        """Return the number of checkpoints included in this query result."""
        return len(self.checkpoints)

    @model_validator(mode="after")
    def validate_checkpoint_sequence(self) -> "DiagnosticCheckpointHistory":
        """Require one unique, newest-first checkpoint sequence for this run."""
        checkpoint_ids: set[str] = set()
        for checkpoint in self.checkpoints:
            if checkpoint.run_id != self.run_id:
                raise ValueError("Checkpoint history cannot contain a different run identity.")
            if checkpoint.checkpoint_id in checkpoint_ids:
                raise ValueError("Checkpoint history cannot contain duplicate checkpoint IDs.")

            checkpoint_ids.add(checkpoint.checkpoint_id)

        for newer, older in zip(self.checkpoints, self.checkpoints[1:], strict=False):
            if newer.created_at < older.created_at:
                raise ValueError("Checkpoint history must be ordered newest first.")

        return self
