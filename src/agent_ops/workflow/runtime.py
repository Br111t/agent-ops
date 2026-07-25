"""Invocation-scoped permissions for Agent-Ops workflow side effects."""

from dataclasses import dataclass

from langgraph.runtime import Runtime


@dataclass(frozen=True, slots=True)
class AgentOpsRuntimeContext:
    """Permissions that expire when one graph invocation finishes."""

    test_execution_approved: bool = False


class TestExecutionApprovalError(PermissionError):
    """Indicate that the current invocation cannot execute repository tests."""


def require_test_execution_approval(
    runtime: Runtime[AgentOpsRuntimeContext],
) -> None:
    """Fail closed unless this invocation explicitly approves test execution."""
    context = runtime.context
    if context is None or not context.test_execution_approved:
        raise TestExecutionApprovalError(
            "Test execution requires explicit approval for the current invocation."
        )
