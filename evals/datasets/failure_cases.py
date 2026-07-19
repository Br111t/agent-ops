"""Versioned deterministic failure-classification cases."""

from agent_ops.models import (
    ClassificationEvaluationCase,
    ClassificationEvaluationDataset,
    EvaluationSourceType,
    FailureCategory,
    NormalizedExecutionEvidence,
    TestFramework,
    TestFrameworkProfile,
)

_PYTEST_PROFILE = TestFrameworkProfile(
    framework=TestFramework.PYTEST,
    confidence=0.95,
    evidence=["pytest configuration found"],
    approved_command=("python", "-m", "pytest", "-q"),
)

_UNKNOWN_PROFILE = TestFrameworkProfile(
    framework=TestFramework.UNKNOWN,
    confidence=0.0,
    evidence=[],
    approved_command=None,
)


def _evidence(**overrides: object) -> NormalizedExecutionEvidence:
    """Create normalized evidence with successful defaults."""
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
    return NormalizedExecutionEvidence(**values)


def _case(
    case_id: str,
    description: str,
    expected_category: FailureCategory,
    *,
    evidence: NormalizedExecutionEvidence | None,
    required_markers: tuple[str, ...],
    framework_profile: TestFrameworkProfile = _PYTEST_PROFILE,
    forbidden_markers: tuple[str, ...] = (),
    expected_abstention: bool = False,
) -> ClassificationEvaluationCase:
    """Create one synthetic trusted classification case."""
    return ClassificationEvaluationCase(
        case_id=case_id,
        source_type=EvaluationSourceType.SYNTHETIC,
        description=description,
        framework_profile=framework_profile,
        normalized_evidence=evidence,
        expected_category=expected_category,
        required_evidence_markers=required_markers,
        forbidden_evidence_markers=forbidden_markers,
        expected_abstention=expected_abstention,
    )


FAILURE_CLASSIFICATION_DATASET = ClassificationEvaluationDataset(
    name="failure-classification-foundation",
    version="1.0.0",
    cases=(
        _case(
            "passed-with-summary",
            "A successful pytest run includes a recognized summary.",
            FailureCategory.PASSED,
            evidence=_evidence(),
            required_markers=("exited with code 0",),
        ),
        _case(
            "passed-without-summary",
            "A zero exit remains successful when the summary is unavailable.",
            FailureCategory.PASSED,
            evidence=_evidence(
                summary_found=False,
                summary_line=None,
                passed=0,
            ),
            required_markers=("exited with code 0",),
        ),
        _case(
            "timeout-partial-output",
            "A timeout is retained even when no complete summary exists.",
            FailureCategory.TIMEOUT,
            evidence=_evidence(
                exit_code=None,
                timed_out=True,
                duration_seconds=120.0,
                summary_found=False,
                summary_line=None,
                passed=0,
            ),
            required_markers=("timed out",),
        ),
        _case(
            "no-tests",
            "Pytest explicitly reports that no tests ran.",
            FailureCategory.NO_TESTS,
            evidence=_evidence(
                exit_code=5,
                summary_line="no tests ran in 0.01s",
                passed=0,
            ),
            required_markers=("no tests ran",),
        ),
        _case(
            "import-error",
            "A module import exception occurs during collection.",
            FailureCategory.IMPORT_ERROR,
            evidence=_evidence(
                exit_code=2,
                passed=0,
                errors=1,
                summary_line="1 error in 0.10s",
                error_tests=("collecting",),
                exception_types=("ModuleNotFoundError",),
            ),
            required_markers=("import exception detected",),
            forbidden_markers=("fixture",),
        ),
        _case(
            "collection-error",
            "A non-import exception occurs while collecting tests.",
            FailureCategory.COLLECTION_ERROR,
            evidence=_evidence(
                exit_code=2,
                passed=0,
                errors=1,
                summary_line="1 error in 0.10s",
                error_tests=("collecting",),
                exception_types=("SyntaxError",),
            ),
            required_markers=("during test collection",),
            forbidden_markers=("import exception",),
        ),
        _case(
            "fixture-setup-error",
            "A setup error includes the repository fixture configuration.",
            FailureCategory.FIXTURE_SETUP_ERROR,
            evidence=_evidence(
                exit_code=1,
                passed=0,
                errors=1,
                summary_line="1 error in 0.10s",
                error_tests=("tests/test_api.py::test_client",),
                exception_types=("RuntimeError",),
                traceback_files=("tests/conftest.py",),
            ),
            required_markers=("fixture configuration file",),
            forbidden_markers=("browser exception",),
        ),
        _case(
            "browser-specific-error",
            "A Playwright target closure identifies a browser failure.",
            FailureCategory.BROWSER_OR_ENVIRONMENT_FAILURE,
            evidence=_evidence(
                exit_code=1,
                passed=0,
                errors=1,
                summary_line="1 error in 0.10s",
                exception_types=("playwright._impl._errors.TargetClosedError",),
                traceback_files=("site-packages/playwright/_impl/_connection.py",),
            ),
            required_markers=("browser exception detected",),
            forbidden_markers=("fixture",),
        ),
        _case(
            "browser-generic-error",
            "A generic environment error is paired with a browser traceback.",
            FailureCategory.BROWSER_OR_ENVIRONMENT_FAILURE,
            evidence=_evidence(
                exit_code=1,
                passed=0,
                failed=1,
                summary_line="1 failed in 0.10s",
                exception_types=("TimeoutError",),
                traceback_files=("site-packages/selenium/webdriver/remote.py",),
            ),
            required_markers=(
                "environment exception detected",
                "browser-library path",
            ),
        ),
        _case(
            "test-data-failure",
            "A data exception originates from an explicit test-data path.",
            FailureCategory.TEST_DATA_FAILURE,
            evidence=_evidence(
                exit_code=1,
                passed=0,
                failed=1,
                summary_line="1 failed in 0.10s",
                exception_types=("json.decoder.JSONDecodeError",),
                traceback_files=("tests/data/payloads.json",),
            ),
            required_markers=(
                "data-related exception",
                "test-data path",
            ),
            forbidden_markers=("application exception",),
        ),
        _case(
            "assertion-failure",
            "An assertion message identifies an expected/actual failure.",
            FailureCategory.ASSERTION_FAILURE,
            evidence=_evidence(
                exit_code=1,
                passed=0,
                failed=1,
                summary_line="1 failed in 0.10s",
                exception_types=("AssertionError",),
                assertion_messages=("assert 1 == 2",),
            ),
            required_markers=("assertion evidence",),
            forbidden_markers=("application exception",),
        ),
        _case(
            "application-failure",
            "A non-assertion exception originates from application source.",
            FailureCategory.APPLICATION_FAILURE,
            evidence=_evidence(
                exit_code=1,
                passed=0,
                failed=1,
                summary_line="1 failed in 0.10s",
                exception_types=("ValueError",),
                traceback_files=("src/example_app/service.py",),
            ),
            required_markers=(
                "application exception detected",
                "application source path",
            ),
            forbidden_markers=("assertion evidence",),
        ),
        _case(
            "broad-test-error",
            "Pytest reports an error without a supported cause marker.",
            FailureCategory.TEST_ERROR,
            evidence=_evidence(
                exit_code=1,
                passed=0,
                errors=1,
                summary_line="1 error in 0.10s",
                error_tests=("tests/test_api.py::test_client",),
                exception_types=("RuntimeError",),
            ),
            required_markers=("reported 1 test error",),
            expected_abstention=True,
        ),
        _case(
            "broad-test-failure",
            "Pytest reports a failure without a supported cause marker.",
            FailureCategory.TEST_FAILURE,
            evidence=_evidence(
                exit_code=1,
                passed=0,
                failed=1,
                summary_line="1 failed in 0.10s",
                failed_tests=("tests/test_math.py::test_add",),
            ),
            required_markers=("reported 1 failed test",),
            expected_abstention=True,
        ),
        _case(
            "unsupported-framework",
            "No approved execution strategy exists for an unknown framework.",
            FailureCategory.UNSUPPORTED_FRAMEWORK,
            evidence=None,
            framework_profile=_UNKNOWN_PROFILE,
            required_markers=("unknown framework",),
        ),
        _case(
            "unparsed-failure",
            "A nonzero exit has no recognizable pytest summary.",
            FailureCategory.UNPARSED_FAILURE,
            evidence=_evidence(
                exit_code=2,
                summary_found=False,
                summary_line=None,
                passed=0,
            ),
            required_markers=(
                "exited with code 2",
                "no recognizable test summary",
            ),
            expected_abstention=True,
        ),
        _case(
            "missing-normalized-evidence",
            "A supported framework has no normalized execution evidence.",
            FailureCategory.UNKNOWN,
            evidence=None,
            required_markers=("no normalized execution evidence",),
            expected_abstention=True,
        ),
        _case(
            "indecisive-evidence",
            "Normalized evidence has no decisive exit status or summary.",
            FailureCategory.UNKNOWN,
            evidence=_evidence(
                exit_code=None,
                summary_found=False,
                summary_line=None,
                passed=0,
            ),
            required_markers=("did not match a deterministic rule",),
            expected_abstention=True,
        ),
    ),
)
