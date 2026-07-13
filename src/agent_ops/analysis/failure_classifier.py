"""Deterministic classification of normalized diagnostic evidence."""

from agent_ops.models import (
    FailureCategory,
    FailureClassification,
    NormalizedExecutionEvidence,
    TestFramework,
    TestFrameworkProfile,
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
                f"Execution timed out after "
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
        return FailureClassification(
            category=FailureCategory.TEST_ERROR,
            confidence=0.99,
            evidence=(
                f"Parsed output reported {evidence.errors} test error(s).",
                *evidence.error_tests,
            ),
            recommended_next_step=(
                "Inspect collection, setup, fixture, import, "
                "or environment errors before evaluating assertions."
            ),
        )

    if evidence.failed > 0:
        return FailureClassification(
            category=FailureCategory.TEST_FAILURE,
            confidence=0.99,
            evidence=(
                f"Parsed output reported {evidence.failed} failed test(s).",
                *evidence.failed_tests,
            ),
            recommended_next_step=(
                "Inspect assertion messages and affected test cases."
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
                "Inspect the captured stdout and stderr and extend "
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


def _reports_no_tests(
    evidence: NormalizedExecutionEvidence,
) -> bool:
    """Return whether the parsed summary explicitly reports no tests."""

    return (
        evidence.summary_found
        and evidence.summary_line is not None
        and evidence.summary_line.startswith("no tests ran in ")
    )