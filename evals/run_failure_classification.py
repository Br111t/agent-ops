"""Run the versioned deterministic failure-classification evaluation."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from agent_ops.evaluation import (
    evaluate_failure_classification,
    write_evaluation_artifact,
)
from evals.datasets import FAILURE_CLASSIFICATION_DATASET


def build_parser() -> argparse.ArgumentParser:
    """Create the classification evaluation argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the deterministic failure-classification evaluation.",
    )
    parser.add_argument(
        "--system-version",
        required=True,
        help=("Immutable implementation identifier, such as a commit SHA or staged Git tree SHA."),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON report path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the evaluation and emit a reproducibly identified JSON report."""
    args = build_parser().parse_args(argv)
    report = evaluate_failure_classification(
        FAILURE_CLASSIFICATION_DATASET,
        system_version=args.system_version,
    )

    if args.output is not None:
        write_evaluation_artifact(report, args.output)

    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
