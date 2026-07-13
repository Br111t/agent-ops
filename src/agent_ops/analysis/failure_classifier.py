"""Deterministic classification of normalized diagnostic evidence."""

from agent_ops.models import (
    FailureCategory,
    FailureClassification,
    NormalizedExecutionEvidence,
    TestFramework,
    TestFrameworkProfile,
)

_IMPORT_EXCEPTION_NAMES = frozenset(
    {
        "ImportError",
        "ModuleNotFoundError",
    }
)

_FIXTURE_EXCEPTION_NAMES = frozenset(
    {
        "FixtureLookupError",
    }
)

_ASSERTION_EXCEPTION_NAMES = frozenset(
    {
        "AssertionError",
    }
)

_BROWSER_EXCEPTION_NAMES = frozenset(
    {
        "BrowserClosedError",
        "NoSuchDriverException",
        "SessionNotCreatedException",
        "TargetClosedError",
        "WebDriverException",
    }
)

_BROWSER_GENERIC_EXCEPTION_NAMES = frozenset(
    {
        "ConnectionError",
        "OSError",
        "TimeoutError",
    }
)

_TEST_DATA_EXCEPTION_NAMES = frozenset(
    {
        "DataError",
        "JSONDecodeError",
        "KeyError",
        "ParserError",
        "UnicodeDecodeError",
        "ValidationError",
    }
)


def classify_failure(
    framework_profile: TestFrameworkProfile,
    normalized_evidence: NormalizedExecutionEvidence | None,
) -> FailureClassification:
    """Classify a diagnostic result using explicit local rules."""

    if framework_profile.framework is TestFramework.UNKNOWN:
        return FailureClassification(
            category=FailureCategory.UNSUPPORTED_FRAMEWORK,
            confidence=1.0,
            evidence=(
                "Framework detection returned an unknown framework.",
            ),
            missing_evidence=(
                "No approved test command is available.",
            ),
            recommended_next_step=(
                "Add support for the repository's test framework "
                "or provide an approved execution strategy."
            ),
        )

    if normalized_evidence is None:
        return FailureClassification(
            category=FailureCategory.UNKNOWN,
            confidence=0.25,
            evidence=(
                "No normalized execution evidence was provided.",
            ),
            missing_evidence=(
                "Execution metadata and parsed test results are missing.",
            ),
            recommended_next_step=(
                "Run the approved test command and normalize its output."
            ),
        )

    evidence = normalized_evidence

    if evidence.timed_out:
        missing_evidence = (
            ()
            if evidence.summary_found
            else ("A complete test summary was not available.",)
        )

        return FailureClassification(
            category=FailureCategory.TIMEOUT,
            confidence=1.0,
            evidence=(
                "Execution timed out after "
                f"{evidence.duration_seconds:.3f} seconds.",
            ),
            missing_evidence=missing_evidence,
            recommended_next_step=(
                "Inspect the hanging test or increase the timeout "
                "only when the expected runtime justifies it."
            ),
        )

    if _reports_no_tests(evidence):
        return FailureClassification(
            category=FailureCategory.NO_TESTS,
            confidence=1.0,
            evidence=(
                evidence.summary_line or "Pytest reported no tests.",
            ),
            recommended_next_step=(
                "Verify test discovery paths, naming conventions, "
                "and pytest configuration."
            ),
        )

    if evidence.errors > 0:
        refined_error = _classify_test_error(evidence)

        if refined_error is not None:
            return refined_error

        return FailureClassification(
            category=FailureCategory.TEST_ERROR,
            confidence=0.99,
            evidence=(
                f"Parsed output reported {evidence.errors} test error(s).",
                *evidence.error_tests,
            ),
            missing_evidence=(
                "No deterministic import, collection, fixture, "
                "or browser/environment marker was found.",
            ),
            recommended_next_step=(
                "Inspect collection, setup, fixture, import, "
                "or environment errors."
            ),
        )

    if evidence.failed > 0:
        refined_failure = _classify_test_failure(evidence)

        if refined_failure is not None:
            return refined_failure

        return FailureClassification(
            category=FailureCategory.TEST_FAILURE,
            confidence=0.99,
            evidence=(
                f"Parsed output reported {evidence.failed} failed test(s).",
                *evidence.failed_tests,
            ),
            missing_evidence=(
                "No deterministic assertion, test-data, application, "
                "or browser/environment marker was found.",
            ),
            recommended_next_step=(
                "Inspect the affected test cases and captured output."
            ),
        )

    if evidence.exit_code == 0:
        missing_evidence = (
            ()
            if evidence.summary_found
            else ("A recognizable test summary was not found.",)
        )

        return FailureClassification(
            category=FailureCategory.PASSED,
            confidence=1.0 if evidence.summary_found else 0.90,
            evidence=(
                "The approved test command exited with code 0.",
                "No test failures or errors were reported.",
            ),
            missing_evidence=missing_evidence,
            recommended_next_step=(
                "Continue with reporting or additional diagnostic checks."
            ),
        )

    if (
        evidence.exit_code is not None
        and evidence.exit_code != 0
        and not evidence.summary_found
    ):
        return FailureClassification(
            category=FailureCategory.UNPARSED_FAILURE,
            confidence=0.85,
            evidence=(
                f"The test command exited with code {evidence.exit_code}.",
                "No recognizable test summary was found.",
            ),
            missing_evidence=(
                "Parsed failure counts and test identifiers are unavailable.",
            ),
            recommended_next_step=(
                "Inspect captured stdout and stderr and extend "
                "the local parser for this output format."
            ),
        )

    return FailureClassification(
        category=FailureCategory.UNKNOWN,
        confidence=0.25,
        evidence=(
            "The available evidence did not match a deterministic rule.",
        ),
        missing_evidence=(
            "A decisive exit status or recognizable summary is missing.",
        ),
        recommended_next_step=(
            "Collect additional local execution evidence before escalation."
        ),
    )


def _classify_test_error(
    evidence: NormalizedExecutionEvidence,
) -> FailureClassification | None:
    """Refine a parsed pytest error using deterministic markers."""

    import_exceptions = _matching_exception_types(
        evidence,
        _IMPORT_EXCEPTION_NAMES,
    )

    if import_exceptions:
        return FailureClassification(
            category=FailureCategory.IMPORT_ERROR,
            confidence=1.0,
            evidence=tuple(
                f"Import exception detected: {exception_type}."
                for exception_type in import_exceptions
            ),
            recommended_next_step=(
                "Verify dependency installation, module paths, "
                "and import configuration."
            ),
        )

    collection_nodes = tuple(
        node_id
        for node_id in evidence.error_tests
        if node_id.lower().startswith("collecting")
    )

    if collection_nodes:
        return FailureClassification(
            category=FailureCategory.COLLECTION_ERROR,
            confidence=0.98,
            evidence=(
                "Pytest reported an error during test collection.",
                *collection_nodes,
            ),
            recommended_next_step=(
                "Run pytest collection diagnostics and inspect "
                "the referenced test modules."
            ),
        )

    browser_evidence = _browser_environment_evidence(evidence)

    if browser_evidence:
        return FailureClassification(
            category=(
                FailureCategory.BROWSER_OR_ENVIRONMENT_FAILURE
            ),
            confidence=0.95,
            evidence=browser_evidence,
            recommended_next_step=(
                "Verify browser installation, driver compatibility, "
                "network access, and runtime environment configuration."
            ),
        )

    fixture_exceptions = _matching_exception_types(
        evidence,
        _FIXTURE_EXCEPTION_NAMES,
    )
    fixture_files = tuple(
        path
        for path in evidence.traceback_files
        if _normalized_path(path).endswith("/conftest.py")
    )

    if fixture_exceptions or fixture_files:
        fixture_evidence = tuple(
            [
                *(
                    f"Fixture exception detected: {exception_type}."
                    for exception_type in fixture_exceptions
                ),
                *(
                    f"Fixture configuration file appeared in traceback: "
                    f"{path}."
                    for path in fixture_files
                ),
            ]
        )

        return FailureClassification(
            category=FailureCategory.FIXTURE_SETUP_ERROR,
            confidence=0.98,
            evidence=fixture_evidence,
            recommended_next_step=(
                "Inspect fixture definitions, dependencies, scope, "
                "and setup logic."
            ),
        )

    return None


def _classify_test_failure(
    evidence: NormalizedExecutionEvidence,
) -> FailureClassification | None:
    """Refine a parsed pytest failure using deterministic markers."""

    browser_evidence = _browser_environment_evidence(evidence)

    if browser_evidence:
        return FailureClassification(
            category=(
                FailureCategory.BROWSER_OR_ENVIRONMENT_FAILURE
            ),
            confidence=0.95,
            evidence=browser_evidence,
            recommended_next_step=(
                "Verify browser state, browser availability, network "
                "access, and environment configuration."
            ),
        )

    data_exceptions = _matching_exception_types(
        evidence,
        _TEST_DATA_EXCEPTION_NAMES,
    )
    data_files = tuple(
        path
        for path in evidence.traceback_files
        if _is_test_data_path(path)
    )

    if data_exceptions and data_files:
        return FailureClassification(
            category=FailureCategory.TEST_DATA_FAILURE,
            confidence=0.90,
            evidence=tuple(
                [
                    *(
                        f"Data-related exception detected: "
                        f"{exception_type}."
                        for exception_type in data_exceptions
                    ),
                    *(
                        f"Test-data path appeared in traceback: {path}."
                        for path in data_files
                    ),
                ]
            ),
            recommended_next_step=(
                "Validate fixture files, generated inputs, schemas, "
                "and test-data assumptions."
            ),
        )

    assertion_exceptions = _matching_exception_types(
        evidence,
        _ASSERTION_EXCEPTION_NAMES,
    )

    if evidence.assertion_messages or assertion_exceptions:
        assertion_evidence = tuple(
            [
                *(
                    f"Assertion exception detected: {exception_type}."
                    for exception_type in assertion_exceptions
                ),
                *(
                    f"Assertion evidence: {message}"
                    for message in evidence.assertion_messages
                ),
            ]
        )

        return FailureClassification(
            category=FailureCategory.ASSERTION_FAILURE,
            confidence=1.0,
            evidence=assertion_evidence,
            recommended_next_step=(
                "Compare the expected and actual values and determine "
                "whether the application or test expectation is incorrect."
            ),
        )

    application_exceptions = tuple(
        exception_type
        for exception_type in evidence.exception_types
        if _exception_name(exception_type)
        not in _ASSERTION_EXCEPTION_NAMES
    )
    application_files = tuple(
        path
        for path in evidence.traceback_files
        if _is_application_path(path)
    )

    if application_exceptions and application_files:
        return FailureClassification(
            category=FailureCategory.APPLICATION_FAILURE,
            confidence=0.85,
            evidence=tuple(
                [
                    *(
                        f"Application exception detected: "
                        f"{exception_type}."
                        for exception_type in application_exceptions
                    ),
                    *(
                        f"Application source path appeared in traceback: "
                        f"{path}."
                        for path in application_files
                    ),
                ]
            ),
            recommended_next_step=(
                "Inspect the application traceback and reproduce "
                "the failing code path independently of the test."
            ),
        )

    return None


def _browser_environment_evidence(
    evidence: NormalizedExecutionEvidence,
) -> tuple[str, ...]:
    """Return browser-specific evidence when deterministic markers exist."""

    specific_exceptions = _matching_exception_types(
        evidence,
        _BROWSER_EXCEPTION_NAMES,
    )

    if specific_exceptions:
        return tuple(
            f"Browser exception detected: {exception_type}."
            for exception_type in specific_exceptions
        )

    generic_exceptions = _matching_exception_types(
        evidence,
        _BROWSER_GENERIC_EXCEPTION_NAMES,
    )
    browser_files = tuple(
        path
        for path in evidence.traceback_files
        if _is_browser_path(path)
    )

    if not generic_exceptions or not browser_files:
        return ()

    return tuple(
        [
            *(
                f"Environment exception detected: {exception_type}."
                for exception_type in generic_exceptions
            ),
            *(
                f"Browser-library path appeared in traceback: {path}."
                for path in browser_files
            ),
        ]
    )


def _matching_exception_types(
    evidence: NormalizedExecutionEvidence,
    expected_names: frozenset[str],
) -> tuple[str, ...]:
    """Return exception types whose final name matches an explicit rule."""

    return tuple(
        exception_type
        for exception_type in evidence.exception_types
        if _exception_name(exception_type) in expected_names
    )


def _exception_name(exception_type: str) -> str:
    """Return the final component of a qualified exception name."""

    return exception_type.rsplit(".", maxsplit=1)[-1]


def _normalized_path(path: str) -> str:
    """Normalize path separators for deterministic matching."""

    return path.replace("\\", "/").lower()


def _is_browser_path(path: str) -> bool:
    """Return whether a traceback path belongs to a browser library."""

    parts = _normalized_path(path).split("/")

    return "playwright" in parts or "selenium" in parts


def _is_test_data_path(path: str) -> bool:
    """Return whether a traceback path explicitly identifies test data."""

    parts = _normalized_path(path).split("/")

    return (
        "data" in parts
        or "fixtures" in parts
        or any("test_data" in part for part in parts)
    )


def _is_application_path(path: str) -> bool:
    """Return whether a traceback path identifies application source."""

    parts = _normalized_path(path).split("/")

    return "src" in parts and "site-packages" not in parts


def _reports_no_tests(
    evidence: NormalizedExecutionEvidence,
) -> bool:
    """Return whether the parsed summary explicitly reports no tests."""

    return (
        evidence.summary_found
        and evidence.summary_line is not None
        and evidence.summary_line.startswith("no tests ran in ")
    )