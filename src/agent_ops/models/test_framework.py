"""Models describing repository test-framework detection."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TestFramework(StrEnum):
    """Test frameworks recognized by Agent-Ops."""

    PYTEST = "pytest"
    UNKNOWN = "unknown"


class TestFrameworkProfile(BaseModel):
    """Structured result from test-framework detection."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    framework: TestFramework
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    approved_command: tuple[str, ...] | None = None
