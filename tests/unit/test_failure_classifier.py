"""Tests for deterministic diagnostic classification."""

import pytest

from agent_ops.analysis import classify_failure
from agent_ops.models import (
    FailureCategory,
)
from agent_ops.models import (
    NormalizedExecutionEvidence as ExecutionEvidence,
)
from agent_ops.models import (
    TestFramework as Framework,
)
from agent_ops.models import (
    TestFrameworkProfile as FrameworkProfile,
)


@pytest.fixture
def pytest_profile() -> FrameworkProfile:
    """Return a supported pytest framework profile."""

    return FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=0.95,
        evidence=["pytest configuration found"],
        approved_command=("python", "-m", "pytest", "-q"),
    )


def make_evidence(
    **overrides: object,
) -> ExecutionEvidence:
    """Create normalized evidence with sensible defaults."""

    values: dict[str, object] = {
        "command": ("python", "-m", "pytest", "-q"),
        "exit_code": 0,
        "timed_out": False,
        "duration_seconds": 0.5,
        "summary_found": True,
        "summary_line": "2 passed in 0.10s",
        "passed": 2,
    }
    values.update(overrides)

    return ExecutionEvidence(**values)


@pytest.mark.parametrize(
    ("evidence", "expected_category"),
    [
        (
            make_evidence(
                exit_code=None,
                timed_out=True,
                summary_found=False,
                summary_line=None,
                passed=0,
                failed=1,
            ),
            FailureCategory.TIMEOUT,
        ),
        (
            make_evidence(
                exit_code=5,
                summary_line="no tests ran in 0.01s",
                passed=0,
            ),
            FailureCategory.NO_TESTS,
        ),
        (
            make_evidence(
                exit_code=1,
                passed=0,
                errors=1,
                error_tests=("tests/test_api.py::test_client",),
            ),
            FailureCategory.TEST_ERROR,
        ),
        (
            make_evidence(
                exit_code=1,
                passed=0,
                failed=1,
                failed_tests=("tests/test_math.py::test_add",),
            ),
            FailureCategory.TEST_FAILURE,
        ),
        (
            make_evidence(),
            FailureCategory.PASSED,
        ),
        (
            make_evidence(
                exit_code=2,
                summary_found=False,
                summary_line=None,
                passed=0,
            ),
            FailureCategory.UNPARSED_FAILURE,
        ),
        (
            make_evidence(
                exit_code=None,
                summary_found=False,
                summary_line=None,
                passed=0,
            ),
            FailureCategory.UNKNOWN,
        ),
    ],
)
def test_classify_failure_uses_explicit_rules(
    pytest_profile: FrameworkProfile,
    evidence: ExecutionEvidence,
    expected_category: FailureCategory,
) -> None:
    """Normalized evidence should map to deterministic categories."""

    result = classify_failure(
        pytest_profile,
        evidence,
    )

    assert result.category is expected_category
    assert 0.0 <= result.confidence <= 1.0
    assert result.evidence
    assert result.recommended_next_step


def test_classify_failure_detects_unsupported_framework() -> None:
    """Unknown frameworks should be rejected before execution."""

    framework_profile = FrameworkProfile(
        framework=Framework.UNKNOWN,
        confidence=0.0,
        evidence=[],
        approved_command=None,
    )

    result = classify_failure(
        framework_profile,
        normalized_evidence=None,
    )

    assert result.category is FailureCategory.UNSUPPORTED_FRAMEWORK
    assert result.confidence == 1.0
    assert result.missing_evidence