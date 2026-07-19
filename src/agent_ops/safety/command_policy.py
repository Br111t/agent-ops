"""Deterministic allowlist policy for repository test commands."""

from collections.abc import Sequence

from agent_ops.models.test_framework import TestFramework, TestFrameworkProfile

APPROVED_PYTEST_COMMAND: tuple[str, ...] = (
    "python",
    "-m",
    "pytest",
    "-q",
)


def is_test_command_approved(
    framework: TestFramework,
    command: Sequence[str] | None,
) -> bool:
    """Return whether a framework and command exactly match the allowlist."""
    if command is None:
        return False

    return framework is TestFramework.PYTEST and tuple(command) == APPROVED_PYTEST_COMMAND


def require_approved_test_command(
    framework_profile: TestFrameworkProfile,
) -> tuple[str, ...]:
    """Return the approved command or reject the profile before execution."""
    command = framework_profile.approved_command

    if not is_test_command_approved(framework_profile.framework, command):
        raise ValueError("Test command is not approved for execution.")

    if command is None:  # pragma: no cover - narrowed by the policy decision above
        raise AssertionError("Approved command unexpectedly missing.")

    return command
