"""Run the versioned deterministic command-safety evaluation."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from agent_ops.evaluation import evaluate_command_safety, write_evaluation_artifact
from evals.datasets import COMMAND_SAFETY_DATASET


def build_parser() -> argparse.ArgumentParser:
    """Create the command-safety evaluation argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the deterministic command-safety evaluation.",
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
    """Evaluate command policy and return a CI-friendly gate status."""
    args = build_parser().parse_args(argv)
    report = evaluate_command_safety(
        COMMAND_SAFETY_DATASET,
        system_version=args.system_version,
    )

    if args.output is not None:
        write_evaluation_artifact(report, args.output)

    print(report.model_dump_json(indent=2))
    return 0 if report.gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
