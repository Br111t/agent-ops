"""LangGraph orchestration for the Agent-Ops diagnostic workflow."""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent_ops.workflow.nodes import (
    detect_framework_node,
    execute_tests_node,
    inspect_repository_node,
    normalize_evidence_node,
    parse_results_node,
)
from agent_ops.workflow.state import AgentOpsState


def should_run_tests(state: AgentOpsState) -> bool:
    """Return whether the workflow should execute repository tests."""

    return state["run_tests"]


def build_diagnostic_graph() -> CompiledStateGraph:
    """Build and compile the Agent-Ops diagnostic workflow."""

    builder = StateGraph(AgentOpsState)

    builder.add_node(
        "inspect_repository",
        inspect_repository_node,
    )
    builder.add_node(
        "detect_framework",
        detect_framework_node,
    )
    builder.add_node(
        "execute_tests",
        execute_tests_node,
    )
    builder.add_node(
        "parse_results",
        parse_results_node,
    )
    builder.add_node(
        "normalize_evidence",
        normalize_evidence_node,
    )

    builder.add_edge(
        START,
        "inspect_repository",
    )
    builder.add_edge(
        "inspect_repository",
        "detect_framework",
    )

    builder.add_conditional_edges(
        "detect_framework",
        should_run_tests,
        {
            True: "execute_tests",
            False: END,
        },
    )

    builder.add_edge(
        "execute_tests",
        "parse_results",
    )
    builder.add_edge(
        "parse_results",
        "normalize_evidence",
    )
    builder.add_edge(
        "normalize_evidence",
        END,
    )

    return builder.compile()
