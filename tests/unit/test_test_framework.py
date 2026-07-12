"""Tests for repository test-framework detection."""

from pathlib import Path

from agent_ops.models import TestFramework as Framework
from agent_ops.repository import detect_test_framework


def test_detect_test_framework_identifies_pytest(
    tmp_path: Path,
) -> None:
    """Pytest configuration should produce an approved command."""
    pyproject = """
[project]
name = "sample-project"
version = "0.1.0"

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
"""

    (tmp_path / "pyproject.toml").write_text(
        pyproject,
        encoding="utf-8",
    )

    result = detect_test_framework(tmp_path)

    assert result.framework is Framework.PYTEST
    assert result.approved_command == (
        "python",
        "-m",
        "pytest",
        "-q",
    )
    assert result.confidence > 0.0
    assert len(result.evidence) == 2


def test_detect_test_framework_returns_unknown(
    tmp_path: Path,
) -> None:
    """A repository without test metadata should remain unknown."""
    (tmp_path / "app.py").write_text("", encoding="utf-8")

    result = detect_test_framework(tmp_path)

    assert result.framework is Framework.UNKNOWN
    assert result.approved_command is None
    assert result.confidence == 0.0
