"""Repository test-framework detection."""

import tomllib
from pathlib import Path
from typing import Any

from agent_ops.models import TestFramework, TestFrameworkProfile


def detect_test_framework(
    repository_path: str | Path,
) -> TestFrameworkProfile:
    """Detect the supported test framework used by a repository."""
    root_path = Path(repository_path).expanduser().resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {root_path}")

    if not root_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {root_path}")

    evidence: list[str] = []
    pyproject_path = root_path / "pyproject.toml"

    if pyproject_path.is_file():
        pyproject = _load_pyproject(pyproject_path)

        if _has_pytest_dependency(pyproject):
            evidence.append("pytest dependency declared in pyproject.toml")

        if _has_pytest_configuration(pyproject):
            evidence.append("pytest configuration declared in pyproject.toml")

    if (root_path / "pytest.ini").is_file():
        evidence.append("pytest.ini found")

    if (root_path / "conftest.py").is_file():
        evidence.append("root conftest.py found")

    if evidence:
        confidence = min(0.95, 0.65 + (0.15 * len(evidence)))

        return TestFrameworkProfile(
            framework=TestFramework.PYTEST,
            confidence=confidence,
            evidence=evidence,
            approved_command=("python", "-m", "pytest", "-q"),
        )

    return TestFrameworkProfile(
        framework=TestFramework.UNKNOWN,
        confidence=0.0,
        evidence=[],
        approved_command=None,
    )


def _load_pyproject(path: Path) -> dict[str, Any]:
    """Load a pyproject.toml file."""
    try:
        with path.open("rb") as pyproject_file:
            return tomllib.load(pyproject_file)
    except tomllib.TOMLDecodeError:
        return {}


def _has_pytest_dependency(pyproject: dict[str, Any]) -> bool:
    """Return whether pytest is declared as a project dependency."""
    project = pyproject.get("project", {})
    dependencies = list(project.get("dependencies", []))

    optional_dependencies = project.get("optional-dependencies", {})

    for dependency_group in optional_dependencies.values():
        dependencies.extend(dependency_group)

    return any(str(dependency).strip().lower().startswith("pytest") for dependency in dependencies)


def _has_pytest_configuration(pyproject: dict[str, Any]) -> bool:
    """Return whether pyproject.toml contains pytest configuration."""
    tool_configuration = pyproject.get("tool", {})
    return "pytest" in tool_configuration
