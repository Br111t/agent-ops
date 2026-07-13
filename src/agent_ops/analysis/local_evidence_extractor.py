"""Conservative local extraction from captured test output."""

import re

from agent_ops.models import (
    ExtractedExecutionDetails,
    TestExecutionResult,
)

_ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"
)

_EXCEPTION_TYPE = r"[A-Za-z_][\w.]*(?:Error|Exception)"
_WARNING_TYPE = r"[A-Za-z_][\w.]*Warning"

_DIRECT_EXCEPTION_PATTERN = re.compile(
    rf"^(?:E\s+)?(?P<type>{_EXCEPTION_TYPE})"
    r"(?::\s*(?P<message>.*))?$"
)

_SHORT_SUMMARY_EXCEPTION_PATTERN = re.compile(
    rf"^(?:FAILED|ERROR)\s+\S+\s+-\s+"
    rf"(?P<type>{_EXCEPTION_TYPE})"
    r"(?::\s*(?P<message>.*))?$"
)

_ASSERTION_PATTERN = re.compile(
    r"^E\s+(?P<message>assert\b.*)$"
)

_WARNING_PATTERN = re.compile(
    rf"^(?:(?:[A-Za-z]:)?[^:\n]+\.py:\d+:\s+)?"
    rf"(?P<type>{_WARNING_TYPE}):\s*(?P<message>.+)$"
)

_PYTEST_FRAME_PATTERN = re.compile(
    rf"^(?P<path>(?:[A-Za-z]:)?[^:\n]+\.py):\d+:"
    rf"(?:\s+in\s+.+|\s+{_EXCEPTION_TYPE}(?::|$))"
)

_PYTHON_FRAME_PATTERN = re.compile(
    r'^\s*File "(?P<path>.+?\.py)", '
    r"line \d+(?:, in .+)?$"
)


def extract_local_evidence(
    execution_result: TestExecutionResult,
) -> ExtractedExecutionDetails:
    """Extract deterministic diagnostic evidence from captured output."""

    combined_output = "\n".join(
        output
        for output in (
            execution_result.stdout,
            execution_result.stderr,
        )
        if output
    )

    exception_types: list[str] = []
    assertion_messages: list[str] = []
    traceback_files: list[str] = []
    warning_messages: list[str] = []

    for raw_line in combined_output.splitlines():
        line = _clean_line(raw_line)

        if not line:
            continue

        frame_match = (
            _PYTEST_FRAME_PATTERN.match(line)
            or _PYTHON_FRAME_PATTERN.match(line)
        )

        if frame_match is not None:
            _append_unique(
                traceback_files,
                frame_match.group("path"),
            )

        warning_match = _WARNING_PATTERN.match(line)

        if warning_match is not None:
            warning_message = (
                f"{warning_match.group('type')}: "
                f"{warning_match.group('message').strip()}"
            )
            _append_unique(
                warning_messages,
                warning_message,
            )
            continue

        assertion_match = _ASSERTION_PATTERN.match(line)

        if assertion_match is not None:
            _append_unique(
                assertion_messages,
                assertion_match.group("message").strip(),
            )

        exception_match = (
            _SHORT_SUMMARY_EXCEPTION_PATTERN.match(line)
            or _DIRECT_EXCEPTION_PATTERN.match(line)
        )

        if exception_match is None:
            continue

        exception_type = exception_match.group("type")
        _append_unique(exception_types, exception_type)

        message = exception_match.group("message")

        if (
            exception_type.rsplit(".", maxsplit=1)[-1]
            == "AssertionError"
            and message
        ):
            _append_unique(
                assertion_messages,
                message.strip(),
            )

    return ExtractedExecutionDetails(
        exception_types=tuple(exception_types),
        assertion_messages=tuple(assertion_messages),
        traceback_files=tuple(traceback_files),
        warning_messages=tuple(warning_messages),
    )


def _clean_line(line: str) -> str:
    """Remove terminal formatting and surrounding whitespace."""

    return _ANSI_ESCAPE_PATTERN.sub("", line).strip()


def _append_unique(values: list[str], value: str) -> None:
    """Append non-empty evidence while preserving discovery order."""

    if value and value not in values:
        values.append(value)