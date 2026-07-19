"""Integration tests for Unicode subprocess evidence capture."""

from pathlib import Path

from agent_ops.models import TestFramework as Framework
from agent_ops.models import TestFrameworkProfile as FrameworkProfile
from agent_ops.tools import execute_approved_tests


def test_execute_approved_tests_captures_unicode_output(tmp_path: Path) -> None:
    """Unicode pytest output should survive the real subprocess boundary."""
    tests_path = tmp_path / "tests"
    tests_path.mkdir()
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\naddopts = -s\ntestpaths = tests\n",
        encoding="utf-8",
    )
    (tests_path / "test_unicode_output.py").write_text(
        'def test_unicode_output():\n    print("✅ → 📄")\n',
        encoding="utf-8",
    )
    framework_profile = FrameworkProfile(
        framework=Framework.PYTEST,
        confidence=0.95,
        evidence=["pytest.ini found"],
        approved_command=("python", "-m", "pytest", "-q"),
    )

    result = execute_approved_tests(
        tmp_path,
        framework_profile,
        timeout_seconds=30,
    )

    assert result.exit_code == 0
    assert "✅ → 📄" in result.stdout
    assert "1 passed" in result.stdout
    assert result.stderr == ""
    assert result.succeeded is True
