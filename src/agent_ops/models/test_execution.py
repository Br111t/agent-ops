"""Models describing controlled test execution."""

from pydantic import BaseModel, ConfigDict, Field


class TestExecutionResult(BaseModel):
    """Structured result from an approved test command."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    command: tuple[str, ...]
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = Field(ge=0.0)
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        """Return whether the test command completed successfully."""
        return not self.timed_out and self.exit_code == 0
