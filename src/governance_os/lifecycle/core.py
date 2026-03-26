"""Pipeline lifecycle state inference engine for governance-os.

Infers the effective lifecycle state of each pipeline from:
- Filesystem marker files (objective evidence)
- Declared state in the contract (author authority)
- Schema validity (contract completeness)
- Dependency graph state (propagated blockage)

Inference is deterministic: same inputs always produce the same outputs.

Marker file conventions
-----------------------
  artifacts/governance/failures/<pipeline-id>.md  — FAILED
  artifacts/governance/blocks/<pipeline-id>.md    — BLOCKED (external)
  artifacts/governance/runs/<pipeline-id>/        — ACTIVE (run in progress)

Declared state takes authority for terminal states (completed, archived).
Marker files take authority for failure and external blockage.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.models.issue import Issue, Severity
from governance_os.models.lifecycle import (
    LifecycleRecord,
    LifecycleResult,
    LifecycleState,
    VALID_DECLARED_STATES,
    _BLOCKING_STATES,
)
from governance_os.models.pipeline import Pipeline


def _infer_single(
    pipeline: Pipeline,
    failures_dir: Path,
    blocks_dir: Path,
    runs_dir: Path,
    graph,
    known: dict[str, LifecycleState],
    has_schema_errors: dict[str, bool],
) -> tuple[LifecycleState | None, list[str]]:
    """Infer effective state for one pipeline.

    Returns (state, reasons) or (None, []) if deps are not yet resolved.
    """
    pid = pipeline.numeric_id

    # 1. Failure marker — objective filesystem evidence, highest priority
    failure_marker = failures_dir / f"{pid}.md"
    if failure_marker.exists():
        return LifecycleState.FAILED, [
            f"Failure marker present: artifacts/governance/failures/{pid}.md"
        ]

    # 2. Declared terminal states — author authority
    decl = pipeline.declared_state.strip().lower()
    if decl == LifecycleState.ARCHIVED:
        return LifecycleState.ARCHIVED, ["Declared archived in contract."]
    if decl == LifecycleState.COMPLETED:
        return LifecycleState.COMPLETED, ["Declared completed in contract."]

    # 3. External block marker
    block_marker = blocks_dir / f"{pid}.md"
    if block_marker.exists():
        return LifecycleState.BLOCKED, [
            f"Block marker present: artifacts/governance/blocks/{pid}.md"
        ]

    # 4. Schema errors → contract not ready
    if has_schema_errors.get(pid, False):
        return LifecycleState.DRAFT, [
            "Contract has schema errors; required sections missing or invalid."
        ]

    # 5. Dependency state — defer until all deps resolved
    prereqs = list(graph.predecessors(pid))
    unresolved = [pr for pr in prereqs if pr not in known]
    if unresolved:
        return None, []  # not ready to infer yet

    blocking_deps = [pr for pr in prereqs if known[pr] in _BLOCKING_STATES]
    if blocking_deps:
        return LifecycleState.BLOCKED, [
            f"Dependency '{pr}' is {known[pr].value}." for pr in blocking_deps
        ]

    # 6. Active run marker
    run_dir = runs_dir / pid
    if run_dir.is_dir():
        return LifecycleState.ACTIVE, [
            f"Active run directory present: artifacts/governance/runs/{pid}/"
        ]

    # 7. No blockers — ready to execute
    return LifecycleState.READY, []


def classify_lifecycle(
    pipelines: list[Pipeline],
    root: Path,
    extra_issues: list[Issue] | None = None,
) -> LifecycleResult:
    """Classify all pipelines into lifecycle states.

    Args:
        pipelines: Full pipeline inventory.
        root: Repository root (used to resolve marker paths).
        extra_issues: Additional issues (e.g. parse errors) to incorporate
            when determining schema validity.

    Returns:
        LifecycleResult with one LifecycleRecord per pipeline.
    """
    if not pipelines:
        return LifecycleResult(root=root, records=[])

    from governance_os.graph.builder import build_graph
    from governance_os.validation.schema import validate_pipeline

    marker_root = root / "artifacts" / "governance"
    failures_dir = marker_root / "failures"
    blocks_dir = marker_root / "blocks"
    runs_dir = marker_root / "runs"

    # Collect schema errors per pipeline
    has_schema_errors: dict[str, bool] = {}
    for p in pipelines:
        errs = [i for i in validate_pipeline(p) if i.severity == Severity.ERROR]
        has_schema_errors[p.numeric_id] = bool(errs)

    # Promote extra_issues parse errors into schema errors
    if extra_issues:
        for issue in extra_issues:
            if issue.pipeline_id and issue.severity == Severity.ERROR:
                has_schema_errors[issue.pipeline_id] = True

    # Build dependency graph
    graph, _ = build_graph(pipelines)

    # Iterative inference — process pipelines until no progress
    effective: dict[str, LifecycleState] = {}
    reasons_map: dict[str, list[str]] = {}

    changed = True
    while changed:
        changed = False
        for p in pipelines:
            pid = p.numeric_id
            if pid in effective:
                continue
            state, reasons = _infer_single(
                p, failures_dir, blocks_dir, runs_dir, graph, effective, has_schema_errors
            )
            if state is not None:
                effective[pid] = state
                reasons_map[pid] = reasons
                changed = True

    # Any pipeline still unresolved is in an unbreakable dependency cycle
    for p in pipelines:
        pid = p.numeric_id
        if pid not in effective:
            effective[pid] = LifecycleState.BLOCKED
            reasons_map[pid] = ["Unresolvable dependency cycle detected."]

    # Build records
    records: list[LifecycleRecord] = []
    for p in pipelines:
        pid = p.numeric_id
        eff = effective[pid]
        decl_raw = p.declared_state.strip().lower()
        # Drift: declared is set, recognised, but differs from effective
        drift = bool(decl_raw) and decl_raw in VALID_DECLARED_STATES and decl_raw != eff.value
        records.append(
            LifecycleRecord(
                pipeline_id=pid,
                slug=p.slug,
                path=p.path,
                declared_state=p.declared_state,
                effective_state=eff,
                drift=drift,
                reasons=reasons_map.get(pid, []),
            )
        )

    return LifecycleResult(root=root, records=records)


def lifecycle_issues(result: LifecycleResult) -> list[Issue]:
    """Derive Issue records from a LifecycleResult for integration with audit/preflight.

    Emits:
    - LIFECYCLE_DRIFT (WARNING) for each pipeline where declared != effective state.
    - LIFECYCLE_FAILED (ERROR) for each FAILED pipeline.
    - LIFECYCLE_INVALID_DECLARED_STATE (WARNING) for unrecognised declared values.

    Args:
        result: LifecycleResult from classify_lifecycle().

    Returns:
        List of Issue records. Empty list means no lifecycle problems.
    """
    issues: list[Issue] = []
    for record in result.records:
        # Unrecognised declared state
        decl = record.declared_state.strip().lower()
        if decl and decl not in VALID_DECLARED_STATES:
            issues.append(
                Issue(
                    code="LIFECYCLE_INVALID_DECLARED_STATE",
                    severity=Severity.WARNING,
                    message=(
                        f"Pipeline '{record.pipeline_id}' ({record.slug}) declares "
                        f"unrecognised state '{record.declared_state}'. "
                        f"Valid states: {', '.join(sorted(VALID_DECLARED_STATES))}."
                    ),
                    path=record.path,
                    pipeline_id=record.pipeline_id,
                    suggestion="Update the 'State:' field to a recognised lifecycle value.",
                )
            )

        # Drift
        if record.drift:
            issues.append(
                Issue(
                    code="LIFECYCLE_DRIFT",
                    severity=Severity.WARNING,
                    message=(
                        f"Pipeline '{record.pipeline_id}' ({record.slug}) lifecycle drift: "
                        f"declared='{record.declared_state}' but effective='{record.effective_state}'."
                    ),
                    path=record.path,
                    pipeline_id=record.pipeline_id,
                    suggestion=(
                        "Update the 'State:' field in the contract to match the inferred "
                        "effective state, or resolve the conditions causing the discrepancy."
                    ),
                )
            )

        # Failed pipelines
        if record.effective_state == LifecycleState.FAILED:
            issues.append(
                Issue(
                    code="LIFECYCLE_FAILED",
                    severity=Severity.ERROR,
                    message=(
                        f"Pipeline '{record.pipeline_id}' ({record.slug}) is in FAILED state. "
                        f"Failure marker: artifacts/governance/failures/{record.pipeline_id}.md"
                    ),
                    path=record.path,
                    pipeline_id=record.pipeline_id,
                    suggestion=(
                        "Investigate the failure marker, resolve the issue, "
                        "and remove the marker file when the pipeline is recovered."
                    ),
                )
            )

    return issues
