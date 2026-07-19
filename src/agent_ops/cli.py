"""Command-line interface for Agent-Ops."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID, uuid4

from agent_ops.models import (
    DiagnosticExecutionReport,
    DiagnosticReport,
    DiagnosticRunStatus,
)
from agent_ops.workflow import build_checkpoint_config, open_sqlite_diagnostic_graph
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
    parser.add_argument(
        "--run-id",
        type=UUID,
        help="Optional UUID to assign as the stable diagnostic run identifier.",
    )
    parser.add_argument(
        "--checkpoint-db",
        type=Path,
        help=(
            "SQLite checkpoint database. Defaults to "
            "$AGENT_OPS_HOME/checkpoints.sqlite3 or ~/.agent-ops/checkpoints.sqlite3."
        ),
    )
    return parser


def build_diagnostic_report(state: AgentOpsState) -> DiagnosticReport:
    """Build the public diagnostic report from completed graph state."""
    if state["run"].status is not DiagnosticRunStatus.COMPLETED:
        raise ValueError("A diagnostic report requires a completed run.")

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
        run=state["run"],
        repository=state["repository_profile"],
        test_framework=state["framework_profile"],
        test_execution=test_execution,
        normalized_evidence=state.get("normalized_evidence"),
        classification=state.get("classification"),
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run the Agent-Ops diagnostic workflow."""
    parser = build_parser()
    args = parser.parse_args(argv)

    run_id = args.run_id or uuid4()
    input_state: AgentOpsState = {
        "repository_path": args.repository_path,
        "run_tests": args.run_tests,
        "run_id": run_id,
    }
    graph_config = build_checkpoint_config(run_id)

    with open_sqlite_diagnostic_graph(
        args.checkpoint_db,
        repository_path=args.repository_path,
    ) as graph:
        if graph.get_state(graph_config).values:
            parser.error(
                "Checkpoint history already exists for this run ID; "
                "resume is not supported by this command yet."
            )

        state = graph.invoke(input_state, graph_config)

    report = build_diagnostic_report(state)

    print(json.dumps(report.to_public_dict(), indent=2))
