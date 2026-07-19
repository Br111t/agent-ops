"""Repository inspection utilities."""

import hashlib
import re
from pathlib import Path, PurePosixPath

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
GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def scan_repository(repository_path: str | Path) -> RepositoryProfile:
    """Inspect a repository and return structured metadata."""
    root_path = Path(repository_path).expanduser().resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {root_path}")

    if not root_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {root_path}")

    files = sorted(
        (
            path
            for path in root_path.rglob("*")
            if _is_inspectable_file(path, root_path) and not _is_ignored(path, root_path)
        ),
        key=lambda path: path.relative_to(root_path).as_posix(),
    )

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
        has_git_directory=(root_path / ".git").exists(),
        git_commit_sha=_read_git_commit(root_path),
        snapshot_sha256=_calculate_snapshot_sha256(files, root_path),
    )


def _calculate_snapshot_sha256(files: list[Path], root_path: Path) -> str:
    """Hash ordered repository paths and contents into one snapshot identifier."""
    digest = hashlib.sha256()

    for path in files:
        relative_path = path.relative_to(root_path).as_posix().encode("utf-8")
        digest.update(len(relative_path).to_bytes(8, byteorder="big"))
        digest.update(relative_path)
        digest.update(path.stat().st_size.to_bytes(16, byteorder="big"))

        with path.open("rb") as source_file:
            while chunk := source_file.read(1024 * 1024):
                digest.update(chunk)

    return digest.hexdigest()


def _read_git_commit(root_path: Path) -> str | None:
    """Read a regular repository's Git HEAD without executing Git or repository code."""
    git_directory = root_path / ".git"

    if git_directory.is_symlink() or not git_directory.is_dir():
        return None

    head_value = _read_small_text_file(git_directory / "HEAD", git_directory)
    if head_value is None:
        return None

    if GIT_SHA_PATTERN.fullmatch(head_value):
        return head_value

    prefix = "ref: "
    if not head_value.startswith(prefix):
        return None

    reference_name = head_value.removeprefix(prefix)
    reference_path = PurePosixPath(reference_name)

    if (
        not reference_name.startswith("refs/")
        or reference_path.is_absolute()
        or ".." in reference_path.parts
    ):
        return None

    loose_reference = _read_small_text_file(
        git_directory.joinpath(*reference_path.parts),
        git_directory,
    )
    if loose_reference is not None and GIT_SHA_PATTERN.fullmatch(loose_reference):
        return loose_reference

    packed_references = _read_small_text_file(
        git_directory / "packed-refs",
        git_directory,
    )
    if packed_references is None:
        return None

    for line in packed_references.splitlines():
        if not line or line.startswith(("#", "^")):
            continue

        commit_sha, separator, packed_reference_name = line.partition(" ")
        if (
            separator
            and packed_reference_name == reference_name
            and GIT_SHA_PATTERN.fullmatch(commit_sha)
        ):
            return commit_sha

    return None


def _read_small_text_file(path: Path, allowed_root: Path) -> str | None:
    """Read bounded Git metadata text and fail closed on inaccessible content."""
    try:
        resolved_path = path.resolve()
        resolved_root = allowed_root.resolve()

        if (
            not resolved_path.is_relative_to(resolved_root)
            or path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > 1024 * 1024
        ):
            return None

        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def _is_ignored(path: Path, root_path: Path) -> bool:
    """Return whether a path belongs to an ignored directory."""
    relative_path = path.relative_to(root_path)

    return any(
        part in IGNORED_DIRECTORIES or part.endswith(".egg-info") for part in relative_path.parts
    )


def _is_inspectable_file(path: Path, root_path: Path) -> bool:
    """Keep snapshot reads within the target repository's regular files."""
    try:
        return path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root_path)
    except OSError:
        return False


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
