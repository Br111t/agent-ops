"""Parsing of captured test-execution evidence."""

import re

from agent_ops.models import TestExecutionResult, TestResultSummary

_COUNT_PATTERN = re.compile(
    r"(?P<count>\d+)\s+"
    r"(?P<status>"
    r"passed|failed|errors?|skipped|xfailed|xpassed|"
    r"deselected|warnings?"
    r")\b"
)

_TEST_NODE_PATTERN = re.compile(
    r"^(?P<status>FAILED|ERROR)\s+(?P<node_id>\S+)"
)

_STATUS_FIELDS = {
    "passed": "passed",
    "failed": "failed",
    "error": "errors",
    "errors": "errors",
    "skipped": "skipped",
    "xfailed": "xfailed",
    "xpassed": "xpassed",
    "deselected": "deselected",
    "warning": "warnings",
    "warnings": "warnings",
}


def parse_pytest_result(
    execution_result: TestExecutionResult,
) -> TestResultSummary:
    """Parse structured evidence from captured pytest output."""
    combined_output = "\n".join(
        output
        for output in (
            execution_result.stdout,
            execution_result.stderr,
        )
        if output
    )

    summary_line = _find_summary_line(combined_output)

    counts = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "deselected": 0,
        "warnings": 0,
    }

    if summary_line is not None:
        for match in _COUNT_PATTERN.finditer(summary_line):
            field_name = _STATUS_FIELDS[match.group("status")]
            counts[field_name] = int(match.group("count"))

    failed_tests, error_tests = _extract_test_nodes(
        combined_output
    )

    return TestResultSummary(
        summary_found=summary_line is not None,
        summary_line=summary_line,
        passed=counts["passed"],
        failed=counts["failed"],
        errors=counts["errors"],
        skipped=counts["skipped"],
        xfailed=counts["xfailed"],
        xpassed=counts["xpassed"],
        deselected=counts["deselected"],
        warnings=counts["warnings"],
        failed_tests=failed_tests,
        error_tests=error_tests,
    )


def _find_summary_line(output: str) -> str | None:
    """Find the final pytest summary line."""
    for raw_line in reversed(output.splitlines()):
        line = raw_line.strip()

        if line.startswith("no tests ran in "):
            return line

        if " in " in line and _COUNT_PATTERN.search(line):
            return line

    return None


def _extract_test_nodes(
    output: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Extract failed and errored pytest node identifiers."""
    failed_tests: list[str] = []
    error_tests: list[str] = []

    for raw_line in output.splitlines():
        match = _TEST_NODE_PATTERN.match(raw_line.strip())

        if match is None:
            continue

        node_id = match.group("node_id")
        status = match.group("status")

        target = (
            failed_tests
            if status == "FAILED"
            else error_tests
        )

        if node_id not in target:
            target.append(node_id)

    return tuple(failed_tests), tuple(error_tests)