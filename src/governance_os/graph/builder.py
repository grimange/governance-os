"""Dependency graph builder for governance-os.

Builds a directed graph from pipeline dependency declarations.
Edge direction: prerequisite → dependent (A → B means A must run before B).
"""

from __future__ import annotations

import networkx as nx

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline

# Sentinel values that mean "no dependencies".
_NO_DEP_TOKENS: frozenset[str] = frozenset({"none", "n/a", "-"})


def build_graph(
    pipelines: list[Pipeline],
) -> tuple[nx.DiGraph, list[Issue]]:
    """Build a dependency graph from a list of pipelines.

    Args:
        pipelines: Full pipeline inventory.

    Returns:
        Tuple of (graph, issues) where issues list unresolved dependencies.
        Graph nodes are numeric_id strings; each node carries a 'pipeline'
        attribute pointing to the Pipeline model.
    """
    known: dict[str, Pipeline] = {p.numeric_id: p for p in pipelines}
    graph: nx.DiGraph = nx.DiGraph()

    # Add all nodes first so isolated pipelines appear in the graph.
    for p in pipelines:
        graph.add_node(p.numeric_id, pipeline=p)

    issues: list[Issue] = []

    for p in pipelines:
        for raw_dep in p.depends_on:
            dep_ref = raw_dep.strip()
            if not dep_ref or dep_ref.lower() in _NO_DEP_TOKENS:
                continue

            if dep_ref not in known:
                issues.append(
                    Issue(
                        code="UNRESOLVED_DEPENDENCY",
                        severity=Severity.ERROR,
                        message=(
                            f"Pipeline '{p.numeric_id}' declares dependency '{dep_ref}' "
                            "which does not match any known pipeline id."
                        ),
                        path=p.path,
                        pipeline_id=p.numeric_id,
                        suggestion=(
                            f"Ensure a pipeline with numeric id '{dep_ref}' exists "
                            "or correct the dependency reference."
                        ),
                    )
                )
            else:
                # Edge: prerequisite → dependent
                graph.add_edge(dep_ref, p.numeric_id)

    return graph, issues
