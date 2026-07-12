"""Command-line interface for Agent-Ops."""

import argparse
import json
from collections.abc import Sequence

from agent_ops.workflow import build_diagnostic_graph


def build_parser() -> argparse.ArgumentParser:
    """Create the Agent-Ops command-line parser."""
    parser = argparse.ArgumentParser(
        prog="agent-ops",
        description="Inspect a repository and return structured metadata.",
    )
    parser.add_argument(
        "repository_path",
        nargs="?",
        default=".",
        help="Repository directory to inspect. Defaults to the current directory.",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Execute the detected approved test command.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Run the Agent-Ops diagnostic workflow."""
    args = build_parser().parse_args(argv)

    graph = build_diagnostic_graph()
    state = graph.invoke(
        {
            "repository_path": args.repository_path,
            "run_tests": args.run_tests,
        }
    )

    repository_profile = state["repository_profile"]
    framework_profile = state["framework_profile"]

    result = {
        "repository": repository_profile.model_dump(mode="json"),
        "test_framework": framework_profile.model_dump(mode="json"),
    }

    if args.run_tests:
        execution_result = state["execution_result"]
        test_summary = state["test_summary"]

        result["test_execution"] = {
            **execution_result.model_dump(mode="json"),
            "succeeded": execution_result.succeeded,
            "summary": test_summary.model_dump(mode="json"),
        }

    print(json.dumps(result, indent=2))
