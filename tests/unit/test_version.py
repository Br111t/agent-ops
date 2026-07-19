"""Tests for Agent-Ops system-version discovery."""

from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

from agent_ops.version import get_agent_ops_version


def test_get_agent_ops_version_reads_installed_package_metadata() -> None:
    """Installed package metadata should identify the running Agent-Ops build."""
    with patch("agent_ops.version.version", return_value="1.2.3"):
        assert get_agent_ops_version() == "1.2.3"


def test_get_agent_ops_version_marks_uninstalled_source() -> None:
    """Source-only execution should return an explicit fallback identifier."""
    with patch(
        "agent_ops.version.version",
        side_effect=PackageNotFoundError,
    ):
        assert get_agent_ops_version() == "uninstalled-source"
