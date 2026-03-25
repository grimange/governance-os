"""Cross-signal derived insights for governance-os.

Detects patterns across multiple finding sets that indicate higher-level
governance problems. Each insight is fully explained — no black-box inference.

Each pattern is documented with:
  - The codes it looks for.
  - The conclusion it draws.
  - Why the combination matters.
"""

from __future__ import annotations

from governance_os.models.issue import Issue
from governance_os.models.score import DerivedInsight


def derive_insights(
    all_findings: list[Issue],
    candidate_count: int = 0,
) -> list[DerivedInsight]:
    """Analyse *all_findings* and return derived cross-signal insights.

    Args:
        all_findings: Combined findings from all governance checks.
        candidate_count: Number of contract candidates discovered (for pattern 1).

    Returns:
        List of DerivedInsight objects, each with a code, title, explanation,
        priority, and the finding codes that triggered it.
    """
    present_codes: set[str] = {i.code for i in all_findings}
    insights: list[DerivedInsight] = []

    # ------------------------------------------------------------------
    # Pattern 1: Uncontracted surfaces + candidates available
    # Trigger: coverage gap exists AND the discover step found candidates.
    # Conclusion: actionable path forward exists — candidates can be promoted.
    # ------------------------------------------------------------------
    if "AUDIT_UNCONTRACTED_SURFACE" in present_codes and candidate_count > 0:
        insights.append(
            DerivedInsight(
                code="INSIGHT_CANDIDATE_READY",
                title="Contract candidates available for uncontracted surfaces",
                explanation=(
                    f"Coverage gaps (AUDIT_UNCONTRACTED_SURFACE) were found alongside "
                    f"{candidate_count} contract candidate(s) from `govos discover candidates`. "
                    "Review candidates and promote them to formal pipeline contracts to close the coverage gap."
                ),
                priority="medium",
                related_findings=["AUDIT_UNCONTRACTED_SURFACE"],
            )
        )

    # ------------------------------------------------------------------
    # Pattern 2: Drift + registry staleness overlap on the same pipeline
    # Trigger: same pipeline_id appears in both AUDIT_MISSING_OUTPUT and
    #          REGISTRY_STALE_ENTRY findings.
    # Conclusion: the pipeline changed without updating governance artifacts.
    # ------------------------------------------------------------------
    drift_pids = {
        i.pipeline_id
        for i in all_findings
        if i.code == "AUDIT_MISSING_OUTPUT" and i.pipeline_id
    }
    stale_pids = {
        i.pipeline_id
        for i in all_findings
        if i.code == "REGISTRY_STALE_ENTRY" and i.pipeline_id
    }
    overlapping = drift_pids & stale_pids
    if overlapping:
        insights.append(
            DerivedInsight(
                code="INSIGHT_PIPELINE_INCONSISTENCY",
                title="Pipeline inconsistency: output drift and registry staleness overlap",
                explanation=(
                    f"Pipeline(s) {sorted(overlapping)} have both missing declared outputs "
                    "(AUDIT_MISSING_OUTPUT) and stale registry entries (REGISTRY_STALE_ENTRY). "
                    "This indicates a pipeline that changed significantly without updating its "
                    "governance artifacts. Update both the registry and verify output declarations."
                ),
                priority="high",
                related_findings=["AUDIT_MISSING_OUTPUT", "REGISTRY_STALE_ENTRY"],
            )
        )

    # ------------------------------------------------------------------
    # Pattern 3: Authority missing + schema violations → governance breakdown
    # Trigger: no authority root AND schema fields missing.
    # Conclusion: dual failure — governance is non-functional at two levels.
    # ------------------------------------------------------------------
    if "AUTHORITY_MISSING_ROOT" in present_codes and "MISSING_REQUIRED_FIELD" in present_codes:
        insights.append(
            DerivedInsight(
                code="INSIGHT_GOVERNANCE_BREAKDOWN",
                title="Governance breakdown: authority configuration and schema compliance both failing",
                explanation=(
                    "The repository is missing its authority configuration (AUTHORITY_MISSING_ROOT) "
                    "and also has schema violations (MISSING_REQUIRED_FIELD). "
                    "Governance is non-functional at both the structural and contract level. "
                    "Restore authority configuration first (`govos init`), then fix schema issues."
                ),
                priority="high",
                related_findings=["AUTHORITY_MISSING_ROOT", "MISSING_REQUIRED_FIELD"],
            )
        )

    # ------------------------------------------------------------------
    # Pattern 4: Multiple documentation deficiencies in the same pipeline
    # Trigger: 2+ quality-related codes on the same pipeline_id.
    # Conclusion: batch remediation is more efficient than fixing one at a time.
    # ------------------------------------------------------------------
    quality_codes = {
        "AUDIT_MISSING_PURPOSE",
        "AUDIT_WEAK_SUCCESS_CRITERIA",
        "AUDIT_MISSING_IMPL_NOTES",
        "AUDIT_MISSING_SCOPE",
    }
    by_pipeline: dict[str, set[str]] = {}
    for issue in all_findings:
        if issue.code in quality_codes and issue.pipeline_id:
            by_pipeline.setdefault(issue.pipeline_id, set()).add(issue.code)

    multi_quality = {pid: codes for pid, codes in by_pipeline.items() if len(codes) >= 2}
    if multi_quality:
        pids = sorted(multi_quality.keys())
        insights.append(
            DerivedInsight(
                code="INSIGHT_CONTRACT_QUALITY_GAP",
                title="Contract quality gap: multiple documentation deficiencies in same pipeline(s)",
                explanation=(
                    f"Pipeline(s) {pids} each have 2 or more documentation quality issues. "
                    "Addressing all deficiencies in a single contract edit is more efficient "
                    "than fixing them incrementally. Review Purpose, Scope, Success Criteria, "
                    "and Implementation Notes sections together."
                ),
                priority="medium",
                related_findings=sorted(quality_codes),
            )
        )

    # ------------------------------------------------------------------
    # Pattern 5: Both dependency cycles and unresolved dependencies
    # Trigger: DEPENDENCY_CYCLE + UNRESOLVED_DEPENDENCY both present.
    # Conclusion: dependency graph is fundamentally broken — fix order matters.
    # ------------------------------------------------------------------
    if "DEPENDENCY_CYCLE" in present_codes and "UNRESOLVED_DEPENDENCY" in present_codes:
        insights.append(
            DerivedInsight(
                code="INSIGHT_GRAPH_INTEGRITY_FAILURE",
                title="Graph integrity failure: dependency cycles and unresolved references coexist",
                explanation=(
                    "Both DEPENDENCY_CYCLE and UNRESOLVED_DEPENDENCY are present. "
                    "The dependency graph is broken in two ways simultaneously. "
                    "Resolve unresolved dependency references first (add missing contracts or fix IDs), "
                    "then re-run to check whether cycles remain."
                ),
                priority="high",
                related_findings=["DEPENDENCY_CYCLE", "UNRESOLVED_DEPENDENCY"],
            )
        )

    return insights
