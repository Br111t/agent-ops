"""Command-line interface for Agent-Ops."""

import argparse
import json
from collections.abc import Sequence

from agent_ops.models import (
    DiagnosticExecutionReport,
    DiagnosticReport,
)
from agent_ops.workflow import build_diagnostic_graph
from agent_ops.workflow.state import AgentOpsState


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


def build_diagnostic_report(state: AgentOpsState) -> DiagnosticReport:
    """Build the public diagnostic report from completed graph state."""
    execution_result = state.get("execution_result")
    test_summary = state.get("test_summary")

    if (execution_result is None) != (test_summary is None):
        raise ValueError("Execution result and test summary must be present together.")

    test_execution = None
    if execution_result is not None and test_summary is not None:
        test_execution = DiagnosticExecutionReport.from_results(
            execution_result,
            test_summary,
        )

    return DiagnosticReport(
        repository=state["repository_profile"],
        test_framework=state["framework_profile"],
        test_execution=test_execution,
        normalized_evidence=state.get("normalized_evidence"),
        classification=state.get("classification"),
    )


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

    report = build_diagnostic_report(state)

    print(json.dumps(report.to_public_dict(), indent=2))