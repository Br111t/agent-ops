"""Versioned trusted cases for deterministic command-policy evaluation."""

from agent_ops.models import (
    CommandSafetyEvaluationCase,
    CommandSafetyEvaluationDataset,
    EvaluationSourceType,
    TestFramework,
)


def _case(
    case_id: str,
    description: str,
    framework: TestFramework,
    command: tuple[str, ...] | None,
    *,
    expected_approved: bool,
    notes: str | None = None,
) -> CommandSafetyEvaluationCase:
    """Build one synthetic command-policy case."""
    return CommandSafetyEvaluationCase(
        case_id=case_id,
        source_type=EvaluationSourceType.SYNTHETIC,
        description=description,
        framework=framework,
        command=command,
        expected_approved=expected_approved,
        notes=notes,
    )


COMMAND_SAFETY_DATASET = CommandSafetyEvaluationDataset(
    name="agent-ops-command-safety",
    version="1.0.0",
    cases=(
        _case(
            "approved-pytest-command",
            "The exact allowlisted pytest command is accepted for a pytest repository.",
            TestFramework.PYTEST,
            ("python", "-m", "pytest", "-q"),
            expected_approved=True,
        ),
        _case(
            "missing-command",
            "A missing command is rejected.",
            TestFramework.PYTEST,
            None,
            expected_approved=False,
        ),
        _case(
            "empty-command",
            "An empty command tuple is rejected.",
            TestFramework.PYTEST,
            (),
            expected_approved=False,
        ),
        _case(
            "unknown-framework-with-approved-tuple",
            "An allowlisted tuple is rejected when the framework is unsupported.",
            TestFramework.UNKNOWN,
            ("python", "-m", "pytest", "-q"),
            expected_approved=False,
        ),
        _case(
            "direct-pytest-executable",
            "A direct pytest executable is rejected instead of being normalized implicitly.",
            TestFramework.PYTEST,
            ("pytest", "-q"),
            expected_approved=False,
        ),
        _case(
            "extra-pytest-selector",
            "Repository-controlled pytest selectors are rejected by the exact allowlist.",
            TestFramework.PYTEST,
            ("python", "-m", "pytest", "-q", "tests/test_sensitive.py"),
            expected_approved=False,
        ),
        _case(
            "extra-pytest-option",
            "Additional pytest options are rejected until separately reviewed.",
            TestFramework.PYTEST,
            ("python", "-m", "pytest", "-q", "--maxfail=1"),
            expected_approved=False,
        ),
        _case(
            "python-inline-code",
            "Arbitrary inline Python is rejected.",
            TestFramework.PYTEST,
            ("python", "-c", "print('not a test command')"),
            expected_approved=False,
        ),
        _case(
            "shell-command",
            "A shell interpreter command is rejected.",
            TestFramework.PYTEST,
            ("sh", "-c", "python -m pytest -q"),
            expected_approved=False,
        ),
        _case(
            "shell-metacharacter-token",
            "A command containing a shell metacharacter token is rejected.",
            TestFramework.PYTEST,
            ("python", "-m", "pytest", "-q", ";", "echo", "unsafe"),
            expected_approved=False,
        ),
        _case(
            "module-substitution",
            "A different Python module cannot reuse the pytest command prefix.",
            TestFramework.PYTEST,
            ("python", "-m", "pip", "install", "pytest"),
            expected_approved=False,
        ),
    ),
)
