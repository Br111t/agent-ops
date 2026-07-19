"""Run the versioned deterministic failure-classification evaluation."""

from agent_ops.evaluation import evaluate_failure_classification
from evals.datasets import FAILURE_CLASSIFICATION_DATASET


def main() -> None:
    """Print the classification evaluation report as JSON."""
    report = evaluate_failure_classification(
        FAILURE_CLASSIFICATION_DATASET,
        system_version="working-tree",
    )
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()