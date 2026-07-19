"""Models describing an inspected repository."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RepositoryProfile(BaseModel):
    """Structured metadata collected during repository inspection."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    root_path: Path
    repository_name: str = Field(min_length=1)
    file_count: int = Field(ge=0)
    detected_languages: list[str] = Field(default_factory=list)
    configuration_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    has_git_directory: bool = False
    git_commit_sha: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40}$",
    )
    snapshot_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
