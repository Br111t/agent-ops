"""Local Agent-Ops configuration defaults."""

import os
from pathlib import Path

AGENT_OPS_HOME_ENVIRONMENT_VARIABLE = "AGENT_OPS_HOME"
DEFAULT_AGENT_OPS_DIRECTORY_NAME = ".agent-ops"


def get_agent_ops_data_directory() -> Path:
    """Return the configurable local directory for durable Agent-Ops data."""
    configured_directory = os.getenv(AGENT_OPS_HOME_ENVIRONMENT_VARIABLE)

    if configured_directory:
        return Path(configured_directory).expanduser().resolve()

    return (Path.home() / DEFAULT_AGENT_OPS_DIRECTORY_NAME).resolve()
