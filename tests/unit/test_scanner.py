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
    assert profile.git_commit_sha is None
    assert profile.snapshot_sha256 is not None
    assert len(profile.snapshot_sha256) == 64


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


def test_scan_repository_snapshot_tracks_only_inspected_files(tmp_path: Path) -> None:
    """Snapshot provenance should change with source, but not ignored content."""
    source_file = tmp_path / "app.py"
    source_file.write_text("version = 1\n", encoding="utf-8")
    ignored_directory = tmp_path / "node_modules"
    ignored_directory.mkdir()
    ignored_file = ignored_directory / "cache.js"
    ignored_file.write_text("ignored = 1\n", encoding="utf-8")

    original_snapshot = scan_repository(tmp_path).snapshot_sha256

    ignored_file.write_text("ignored = 2\n", encoding="utf-8")
    assert scan_repository(tmp_path).snapshot_sha256 == original_snapshot

    source_file.write_text("version = 2\n", encoding="utf-8")
    assert scan_repository(tmp_path).snapshot_sha256 != original_snapshot


def test_scan_repository_reads_loose_git_head_without_running_git(tmp_path: Path) -> None:
    """A regular loose Git reference should be captured as optional provenance."""
    commit_sha = "b" * 40
    reference_directory = tmp_path / ".git" / "refs" / "heads"
    reference_directory.mkdir(parents=True)
    (tmp_path / ".git" / "HEAD").write_text(
        "ref: refs/heads/main\n",
        encoding="utf-8",
    )
    (reference_directory / "main").write_text(f"{commit_sha}\n", encoding="utf-8")

    profile = scan_repository(tmp_path)

    assert profile.git_commit_sha == commit_sha


def test_scan_repository_reads_packed_git_head(tmp_path: Path) -> None:
    """Packed branch references should be supported without invoking Git."""
    commit_sha = "c" * 40
    git_directory = tmp_path / ".git"
    git_directory.mkdir()
    (git_directory / "HEAD").write_text(
        "ref: refs/heads/main\n",
        encoding="utf-8",
    )
    (git_directory / "packed-refs").write_text(
        f"# pack-refs with: peeled fully-peeled\n{commit_sha} refs/heads/main\n",
        encoding="utf-8",
    )

    profile = scan_repository(tmp_path)

    assert profile.git_commit_sha == commit_sha


def test_scan_repository_rejects_git_reference_traversal(tmp_path: Path) -> None:
    """Malformed Git references should fail closed instead of escaping metadata."""
    git_directory = tmp_path / ".git"
    git_directory.mkdir()
    (git_directory / "HEAD").write_text(
        "ref: refs/../../outside\n",
        encoding="utf-8",
    )

    profile = scan_repository(tmp_path)

    assert profile.git_commit_sha is None
