"""Normalization of captured test-execution evidence."""

from agent_ops.models import (
    NormalizedExecutionEvidence,
    TestExecutionResult,
    TestResultSummary,
)


def normalize_execution_evidence(
    execution_result: TestExecutionResult,
    test_summary: TestResultSummary,
) -> NormalizedExecutionEvidence:
    """Combine raw execution metadata and parsed test results."""

    return NormalizedExecutionEvidence(
        command=execution_result.command,
        exit_code=execution_result.exit_code,
        timed_out=execution_result.timed_out,
        duration_seconds=execution_result.duration_seconds,
        summary_found=test_summary.summary_found,
        summary_line=test_summary.summary_line,
        passed=test_summary.passed,
        failed=test_summary.failed,
        errors=test_summary.errors,
        skipped=test_summary.skipped,
        xfailed=test_summary.xfailed,
        xpassed=test_summary.xpassed,
        deselected=test_summary.deselected,
        warning_count=test_summary.warnings,
        failed_tests=test_summary.failed_tests,
        error_tests=test_summary.error_tests,
    )