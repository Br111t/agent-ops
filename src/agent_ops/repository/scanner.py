"""Repository inspection utilities."""

from pathlib import Path

from agent_ops.models import RepositoryProfile

IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}

LANGUAGE_BY_SUFFIX = {
    ".ipynb": "Jupyter Notebook",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".py": "Python",
    ".sql": "SQL",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
}

CONFIGURATION_FILENAMES = {
    ".env.example",
    "Dockerfile",
    "build.gradle",
    "build.gradle.kts",
    "docker-compose.yaml",
    "docker-compose.yml",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
}

TEST_DIRECTORY_NAMES = {"test", "tests"}
NON_TEST_DIRECTORY_NAMES = {"fixtures", "data", "resources"}


def scan_repository(repository_path: str | Path) -> RepositoryProfile:
    """Inspect a repository and return structured metadata."""
    root_path = Path(repository_path).expanduser().resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {root_path}")

    if not root_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {root_path}")

    files = [
        path for path in root_path.rglob("*") if path.is_file() and not _is_ignored(path, root_path)
    ]

    detected_languages = sorted(
        {language for path in files if (language := LANGUAGE_BY_SUFFIX.get(path.suffix.lower()))}
    )

    configuration_files = sorted(
        path.relative_to(root_path).as_posix()
        for path in files
        if path.name in CONFIGURATION_FILENAMES
    )

    test_files = sorted(
        path.relative_to(root_path).as_posix() for path in files if _is_test_file(path, root_path)
    )

    return RepositoryProfile(
        root_path=root_path,
        repository_name=root_path.name,
        file_count=len(files),
        detected_languages=detected_languages,
        configuration_files=configuration_files,
        test_files=test_files,
        has_git_directory=(root_path / ".git").is_dir(),
    )


def _is_ignored(path: Path, root_path: Path) -> bool:
    """Return whether a path belongs to an ignored directory."""
    relative_path = path.relative_to(root_path)

    return any(
        part in IGNORED_DIRECTORIES or part.endswith(".egg-info") for part in relative_path.parts
    )


def _is_test_file(path: Path, root_path: Path) -> bool:
    """Return whether a file appears to be an executable test module."""
    relative_path = path.relative_to(root_path)
    directory_names = {part.lower() for part in relative_path.parts[:-1]}
    filename = path.name.lower()

    if directory_names & NON_TEST_DIRECTORY_NAMES:
        return False

    if directory_names & TEST_DIRECTORY_NAMES:
        return filename.startswith("test_") or filename.endswith("_test.py")

    # Allow conventional root-level Python tests while avoiding
    # application modules such as src/.../test_runner.py.
    return path.parent == root_path and (
        filename.startswith("test_") or filename.endswith("_test.py")
    )
