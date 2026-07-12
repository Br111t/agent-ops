"""Tests for repository scanning."""

from pathlib import Path

import pytest

from agent_ops.repository import scan_repository


def test_scan_repository_returns_structured_profile(tmp_path: Path) -> None:
    """Repository files should be converted into structured metadata."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "node_modules").mkdir()

    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "src" / "app.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "tests" / "test_app.py").write_text("", encoding="utf-8")
    (tmp_path / "node_modules" / "ignored.js").write_text("", encoding="utf-8")

    profile = scan_repository(tmp_path)

    assert profile.repository_name == tmp_path.name
    assert profile.file_count == 3
    assert profile.detected_languages == ["Python"]
    assert profile.configuration_files == ["pyproject.toml"]
    assert profile.test_files == ["tests/test_app.py"]
    assert profile.has_git_directory is True


def test_scan_repository_rejects_missing_path(tmp_path: Path) -> None:
    """A missing repository path should raise a clear error."""
    missing_path = tmp_path / "missing"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        scan_repository(missing_path)


def test_scan_repository_excludes_tools_and_fixtures(tmp_path: Path) -> None:
    """Test helpers and fixture data should not be reported as tests."""
    tools_directory = tmp_path / "src" / "agent_ops" / "tools"
    fixtures_directory = tmp_path / "tests" / "fixtures"
    tests_directory = tmp_path / "tests" / "unit"

    tools_directory.mkdir(parents=True)
    fixtures_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)

    (tools_directory / "test_runner.py").write_text("", encoding="utf-8")
    (fixtures_directory / "sample_pytest_repo.py").write_text("", encoding="utf-8")
    (tests_directory / "test_scanner.py").write_text("", encoding="utf-8")

    profile = scan_repository(tmp_path)

    assert profile.test_files == ["tests/unit/test_scanner.py"]