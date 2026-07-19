"""Compare baseline and candidate failure-classification reports."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from agent_ops.evaluation import (
    compare_classification_reports,
    load_classification_report,
    write_evaluation_artifact,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the report-comparison argument parser."""
    parser = argparse.ArgumentParser(
        description="Compare classification reports and fail on regressions.",
    )
    parser.add_argument(
        "baseline_report",
        type=Path,
        help="JSON report produced by the accepted baseline version.",
    )
    parser.add_argument(
        "candidate_report",
        type=Path,
        help="JSON report produced by the candidate version.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON comparison report path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Compare reports, emit the result, and return the regression gate status."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        baseline = load_classification_report(args.baseline_report)
        candidate = load_classification_report(args.candidate_report)
        comparison = compare_classification_reports(baseline, candidate)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.output is not None:
        write_evaluation_artifact(comparison, args.output)

    print(comparison.model_dump_json(indent=2))
    return 0 if comparison.gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
