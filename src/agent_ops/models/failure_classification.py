"""Models describing deterministic diagnostic classifications."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FailureCategory(StrEnum):
    """Categories produced by deterministic local analysis."""

    PASSED = "passed"
    TIMEOUT = "timeout"
    NO_TESTS = "no_tests"
    TEST_ERROR = "test_error"
    TEST_FAILURE = "test_failure"
    UNSUPPORTED_FRAMEWORK = "unsupported_framework"
    UNPARSED_FAILURE = "unparsed_failure"

    COLLECTION_ERROR = "collection_error"
    FIXTURE_SETUP_ERROR = "fixture_setup_error"
    IMPORT_ERROR = "import_error"
    ASSERTION_FAILURE = "assertion_failure"
    BROWSER_OR_ENVIRONMENT_FAILURE = "browser_or_environment_failure"
    TEST_DATA_FAILURE = "test_data_failure"
    APPLICATION_FAILURE = "application_failure"

    UNKNOWN = "unknown"


class FailureClassification(BaseModel):
    """Evidence-supported classification of a diagnostic result."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    category: FailureCategory
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    recommended_next_step: str = Field(min_length=1)
