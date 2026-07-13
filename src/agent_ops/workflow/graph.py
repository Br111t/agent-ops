"""LangGraph orchestration for the Agent-Ops diagnostic workflow."""

from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent_ops.models import TestFramework
from agent_ops.workflow.nodes import (
    classify_result_node,
    detect_framework_node,
    execute_tests_node,
    inspect_repository_node,
    normalize_evidence_node,
    parse_results_node,
)
from agent_ops.workflow.state import AgentOpsState


def route_after_framework_detection(
    state: AgentOpsState,
) -> Literal["skip", "classify", "execute"]:
    """Choose whether to stop, classify, or execute tests."""

    if not state["run_tests"]:
        return "skip"

    if (
        state["framework_profile"].framework
        is TestFramework.UNKNOWN
    ):
        return "classify"

    return "execute"


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
    builder.add_node(
        "classify_result",
        classify_result_node,
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
        route_after_framework_detection,
        {
            "skip": END,
            "classify": "classify_result",
            "execute": "execute_tests",
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
        "classify_result",
    )
    builder.add_edge(
        "classify_result",
        END,
    )

    return builder.compile()
