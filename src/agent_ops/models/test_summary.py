"""Models describing parsed test-execution evidence."""

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TestResultSummary(BaseModel):
    """Structured summary parsed from pytest output."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    summary_found: bool = False
    summary_line: str | None = None

    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    xfailed: int = Field(default=0, ge=0)
    xpassed: int = Field(default=0, ge=0)
    deselected: int = Field(default=0, ge=0)
    warnings: int = Field(default=0, ge=0)

    failed_tests: tuple[str, ...] = ()
    error_tests: tuple[str, ...] = ()

    @computed_field
    @property
    def total_tests(self) -> int:
        """Return the number of tests represented by test outcomes."""
        return self.passed + self.failed + self.errors + self.skipped + self.xfailed + self.xpassed
