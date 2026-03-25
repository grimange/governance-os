"""Readiness and blockage classification for governance-os.

Classifies each pipeline into an operational state that Codex can use
to determine what is actionable next.

Classification is deterministic and derived solely from:
- Schema validation results
- Graph-level diagnostics (unresolved deps, cycles)
- Prerequisite states (propagated blockage)
"""

from __future__ import annotations

from pathlib import Path

from governance_os.graph.analysis import detect_cycles, direct_prerequisites
from governance_os.graph.builder import build_graph
from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline
from governance_os.models.status import PipelineStatus, StatusRecord, StatusResult
from governance_os.validation.schema import validate_pipeline


def classify(
    pipelines: list[Pipeline],
    *,
    extra_issues: list[Issue] | None = None,
) -> StatusResult:
    """Classify all pipelines into operational states.

    Args:
        pipelines: Full pipeline inventory.
        extra_issues: Additional issues (e.g. from integrity validation).

    Returns:
        StatusResult with one StatusRecord per pipeline.
    """
    if not pipelines:
        return StatusResult(root=Path("."), records=[])

    root = pipelines[0].path.parent

    # --- Schema validation ---
    schema_issues: dict[str, list[Issue]] = {p.numeric_id: [] for p in pipelines}
    for p in pipelines:
        schema_issues[p.numeric_id] = validate_pipeline(p)

    # --- Graph construction and cycle detection ---
    graph, graph_issues = build_graph(pipelines)
    cycle_issues = detect_cycles(graph)

    # Collect all graph-level issue pipeline_ids.
    graph_error_ids: set[str] = set()
    for issue in graph_issues + cycle_issues:
        if issue.pipeline_id:
            graph_error_ids.add(issue.pipeline_id)

    # Merge extra issues.
    extra: list[Issue] = extra_issues or []
    extra_error_ids: set[str] = {
        i.pipeline_id for i in extra if i.pipeline_id and i.severity == Severity.ERROR
    }

    # --- Per-pipeline classification ---
    # First pass: mark invalid pipelines.
    status_map: dict[str, PipelineStatus] = {}
    reasons_map: dict[str, list[str]] = {p.numeric_id: [] for p in pipelines}

    for p in pipelines:
        pid = p.numeric_id
        errors = [i for i in schema_issues[pid] if i.severity == Severity.ERROR]
        if errors or pid in extra_error_ids:
            status_map[pid] = PipelineStatus.INVALID
            reasons_map[pid] = [i.message for i in errors]

    # Second pass: mark blocked (graph-level issues or invalid prerequisites).
    # Iterate until stable (propagate blockage through the graph).
    changed = True
    while changed:
        changed = False
        for p in pipelines:
            pid = p.numeric_id
            if pid in status_map:
                continue  # already classified

            if pid in graph_error_ids:
                status_map[pid] = PipelineStatus.BLOCKED
                reasons_map[pid] = [
                    i.message for i in graph_issues + cycle_issues if i.pipeline_id == pid
                ]
                changed = True
                continue

            # Check if any direct prerequisite is invalid or blocked.
            prereqs = direct_prerequisites(graph, pid)
            blocking = [
                pr
                for pr in prereqs
                if status_map.get(pr) in (PipelineStatus.INVALID, PipelineStatus.BLOCKED)
            ]
            if blocking:
                status_map[pid] = PipelineStatus.BLOCKED
                reasons_map[pid] = [
                    f"Prerequisite '{pr}' is {status_map[pr].value}." for pr in blocking
                ]
                changed = True

    # Third pass: classify remaining as ready or orphaned.
    for p in pipelines:
        pid = p.numeric_id
        if pid in status_map:
            continue

        has_predecessors = bool(list(graph.predecessors(pid)))
        has_successors = bool(list(graph.successors(pid)))

        if not has_predecessors and not has_successors:
            status_map[pid] = PipelineStatus.ORPHANED
            reasons_map[pid] = ["Pipeline has no declared dependencies and no dependents."]
        else:
            status_map[pid] = PipelineStatus.READY

    # --- Build result ---
    records = [
        StatusRecord(
            pipeline_id=p.numeric_id,
            slug=p.slug,
            path=p.path,
            status=status_map[p.numeric_id],
            reasons=reasons_map[p.numeric_id],
        )
        for p in pipelines
    ]

    return StatusResult(root=Path(root), records=records)
