"""Agent-Ops package-version provenance."""

from importlib.metadata import PackageNotFoundError, version


def get_agent_ops_version() -> str:
    """Return the installed Agent-Ops package version or an explicit source fallback."""
    try:
        return version("agent-ops")
    except PackageNotFoundError:
        return "uninstalled-source"
