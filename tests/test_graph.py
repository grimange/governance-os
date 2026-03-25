"""Tests for governance_os.graph.builder and analysis."""

from pathlib import Path

from governance_os.graph.analysis import (
    detect_cycles,
    direct_dependents,
    direct_prerequisites,
    downstream,
    upstream,
)
from governance_os.graph.builder import build_graph
from governance_os.models.pipeline import Pipeline


def _p(id_, slug, deps=None):
    return Pipeline(
        numeric_id=id_,
        slug=slug,
        path=Path(f"pipelines/{id_}--{slug}.md"),
        depends_on=deps or [],
    )


def test_build_graph_nodes():
    pipelines = [_p("001", "a"), _p("002", "b")]
    graph, issues = build_graph(pipelines)
    assert "001" in graph
    assert "002" in graph
    assert issues == []


def test_build_graph_edge_direction():
    # 002 depends on 001 → edge 001→002
    pipelines = [_p("001", "a"), _p("002", "b", ["001"])]
    graph, _ = build_graph(pipelines)
    assert graph.has_edge("001", "002")
    assert not graph.has_edge("002", "001")


def test_none_sentinel_ignored():
    pipelines = [_p("001", "a", ["none"]), _p("002", "b", ["n/a"])]
    graph, issues = build_graph(pipelines)
    assert issues == []
    assert list(graph.edges()) == []


def test_unresolved_dependency():
    pipelines = [_p("001", "a", ["999"])]
    _, issues = build_graph(pipelines)
    assert any(i.code == "UNRESOLVED_DEPENDENCY" for i in issues)


def test_no_cycles_in_linear_chain():
    pipelines = [_p("001", "a"), _p("002", "b", ["001"]), _p("003", "c", ["002"])]
    graph, _ = build_graph(pipelines)
    assert detect_cycles(graph) == []


def test_cycle_detected():
    pipelines = [_p("001", "a", ["002"]), _p("002", "b", ["001"])]
    graph, _ = build_graph(pipelines)
    issues = detect_cycles(graph)
    assert any(i.code == "DEPENDENCY_CYCLE" for i in issues)


def test_upstream_transitive():
    pipelines = [_p("001", "a"), _p("002", "b", ["001"]), _p("003", "c", ["002"])]
    graph, _ = build_graph(pipelines)
    assert upstream(graph, "003") == ["001", "002"]


def test_downstream_transitive():
    pipelines = [_p("001", "a"), _p("002", "b", ["001"]), _p("003", "c", ["002"])]
    graph, _ = build_graph(pipelines)
    assert downstream(graph, "001") == ["002", "003"]


def test_direct_prerequisites():
    pipelines = [_p("001", "a"), _p("002", "b"), _p("003", "c", ["001", "002"])]
    graph, _ = build_graph(pipelines)
    assert direct_prerequisites(graph, "003") == ["001", "002"]


def test_direct_dependents():
    pipelines = [_p("001", "a"), _p("002", "b", ["001"]), _p("003", "c", ["001"])]
    graph, _ = build_graph(pipelines)
    assert direct_dependents(graph, "001") == ["002", "003"]


def test_isolated_node_has_no_upstream_downstream():
    pipelines = [_p("001", "a")]
    graph, _ = build_graph(pipelines)
    assert upstream(graph, "001") == []
    assert downstream(graph, "001") == []


def test_missing_node_returns_empty():
    pipelines = [_p("001", "a")]
    graph, _ = build_graph(pipelines)
    assert upstream(graph, "999") == []
    assert downstream(graph, "999") == []
