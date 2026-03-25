"""Graph diagnostics for governance-os.

Analyses the dependency graph for structural problems and exposes
upstream/downstream relationship queries.
"""

from __future__ import annotations

import networkx as nx

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline


def detect_cycles(graph: nx.DiGraph) -> list[Issue]:
    """Detect circular dependencies in the graph.

    Args:
        graph: Dependency graph produced by builder.build_graph.

    Returns:
        One Issue per cycle found, with ERROR severity.
    """
    issues: list[Issue] = []
    try:
        cycles = list(nx.simple_cycles(graph))
    except nx.NetworkXNoCycle:
        return []

    for cycle in cycles:
        cycle_str = " → ".join(cycle + [cycle[0]])
        for node_id in cycle:
            pipeline: Pipeline | None = graph.nodes[node_id].get("pipeline")
            path = pipeline.path if pipeline else None
            issues.append(
                Issue(
                    code="DEPENDENCY_CYCLE",
                    severity=Severity.ERROR,
                    message=f"Circular dependency detected: {cycle_str}",
                    path=path,
                    pipeline_id=node_id,
                    suggestion="Remove or reorder the dependencies to break the cycle.",
                )
            )

    return issues


def upstream(graph: nx.DiGraph, pipeline_id: str) -> list[str]:
    """Return ids of all pipelines that *pipeline_id* transitively depends on.

    Args:
        graph: Dependency graph.
        pipeline_id: Numeric id of the target pipeline.

    Returns:
        Sorted list of upstream pipeline ids.
    """
    if pipeline_id not in graph:
        return []
    return sorted(nx.ancestors(graph, pipeline_id))


def downstream(graph: nx.DiGraph, pipeline_id: str) -> list[str]:
    """Return ids of all pipelines that transitively depend on *pipeline_id*.

    Args:
        graph: Dependency graph.
        pipeline_id: Numeric id of the target pipeline.

    Returns:
        Sorted list of downstream pipeline ids.
    """
    if pipeline_id not in graph:
        return []
    return sorted(nx.descendants(graph, pipeline_id))


def direct_prerequisites(graph: nx.DiGraph, pipeline_id: str) -> list[str]:
    """Return ids of the immediate prerequisites of *pipeline_id*."""
    if pipeline_id not in graph:
        return []
    return sorted(graph.predecessors(pipeline_id))


def direct_dependents(graph: nx.DiGraph, pipeline_id: str) -> list[str]:
    """Return ids of pipelines that directly depend on *pipeline_id*."""
    if pipeline_id not in graph:
        return []
    return sorted(graph.successors(pipeline_id))
