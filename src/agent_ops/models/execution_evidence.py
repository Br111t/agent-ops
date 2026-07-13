"""Models describing normalized test-execution evidence."""

from pydantic import BaseModel, ConfigDict, Field


class NormalizedExecutionEvidence(BaseModel):
    """Consistent evidence derived from execution and parsed test results."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    command: tuple[str, ...]
    exit_code: int | None
    timed_out: bool
    duration_seconds: float = Field(ge=0.0)

    summary_found: bool
    summary_line: str | None = None

    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    xfailed: int = Field(default=0, ge=0)
    xpassed: int = Field(default=0, ge=0)
    deselected: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)

    failed_tests: tuple[str, ...] = ()
    error_tests: tuple[str, ...] = ()

    exception_types: tuple[str, ...] = ()
    assertion_messages: tuple[str, ...] = ()
    traceback_files: tuple[str, ...] = ()
    warning_messages: tuple[str, ...] = ()


class ExtractedExecutionDetails(BaseModel):
    """Detailed evidence conservatively extracted from test output."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    exception_types: tuple[str, ...] = ()
    assertion_messages: tuple[str, ...] = ()
    traceback_files: tuple[str, ...] = ()
    warning_messages: tuple[str, ...] = ()