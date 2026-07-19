"""Read and write machine-readable evaluation artifacts."""

from pathlib import Path

from agent_ops.models import (
    ClassificationEvaluationComparison,
    ClassificationEvaluationReport,
)

EvaluationArtifact = ClassificationEvaluationReport | ClassificationEvaluationComparison


def load_classification_report(path: Path) -> ClassificationEvaluationReport:
    """Load and validate a classification evaluation report from JSON."""
    return ClassificationEvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))


def write_evaluation_artifact(
    artifact: EvaluationArtifact,
    path: Path,
) -> None:
    """Write a validated evaluation artifact as stable, formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{artifact.model_dump_json(indent=2)}\n",
        encoding="utf-8",
    )
