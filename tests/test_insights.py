"""Tests for the cross-signal derived insights module."""

from governance_os.intelligence.insights import derive_insights
from governance_os.models.issue import Issue, Severity


def _issue(code: str, severity: Severity = Severity.WARNING, pipeline_id: str | None = None) -> Issue:
    return Issue(code=code, severity=severity, message="test", pipeline_id=pipeline_id)


# ---------------------------------------------------------------------------
# Pattern 1: Uncontracted surface + candidates available
# ---------------------------------------------------------------------------


def test_no_insight_when_no_surface_finding() -> None:
    insights = derive_insights([], candidate_count=5)
    codes = [i.code for i in insights]
    assert "INSIGHT_CANDIDATE_READY" not in codes


def test_no_insight_when_surface_but_no_candidates() -> None:
    findings = [_issue("AUDIT_UNCONTRACTED_SURFACE")]
    insights = derive_insights(findings, candidate_count=0)
    codes = [i.code for i in insights]
    assert "INSIGHT_CANDIDATE_READY" not in codes


def test_insight_candidate_ready_triggered() -> None:
    findings = [_issue("AUDIT_UNCONTRACTED_SURFACE")]
    insights = derive_insights(findings, candidate_count=3)
    codes = [i.code for i in insights]
    assert "INSIGHT_CANDIDATE_READY" in codes


def test_candidate_ready_insight_priority_is_medium() -> None:
    findings = [_issue("AUDIT_UNCONTRACTED_SURFACE")]
    insights = derive_insights(findings, candidate_count=1)
    insight = next(i for i in insights if i.code == "INSIGHT_CANDIDATE_READY")
    assert insight.priority == "medium"


# ---------------------------------------------------------------------------
# Pattern 2: Drift + registry staleness overlap on same pipeline
# ---------------------------------------------------------------------------


def test_no_inconsistency_when_different_pipelines() -> None:
    findings = [
        _issue("AUDIT_MISSING_OUTPUT", pipeline_id="001"),
        _issue("REGISTRY_STALE_ENTRY", pipeline_id="002"),
    ]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_PIPELINE_INCONSISTENCY" not in codes


def test_inconsistency_triggered_on_same_pipeline() -> None:
    findings = [
        _issue("AUDIT_MISSING_OUTPUT", pipeline_id="001"),
        _issue("REGISTRY_STALE_ENTRY", pipeline_id="001"),
    ]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_PIPELINE_INCONSISTENCY" in codes


def test_inconsistency_insight_priority_is_high() -> None:
    findings = [
        _issue("AUDIT_MISSING_OUTPUT", pipeline_id="001"),
        _issue("REGISTRY_STALE_ENTRY", pipeline_id="001"),
    ]
    insights = derive_insights(findings)
    insight = next(i for i in insights if i.code == "INSIGHT_PIPELINE_INCONSISTENCY")
    assert insight.priority == "high"


def test_no_inconsistency_when_no_pipeline_id() -> None:
    """Findings without pipeline_id cannot form the overlap pattern."""
    findings = [
        _issue("AUDIT_MISSING_OUTPUT"),  # no pipeline_id
        _issue("REGISTRY_STALE_ENTRY"),  # no pipeline_id
    ]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_PIPELINE_INCONSISTENCY" not in codes


# ---------------------------------------------------------------------------
# Pattern 3: Authority missing + schema violations
# ---------------------------------------------------------------------------


def test_governance_breakdown_requires_both_codes() -> None:
    findings = [_issue("AUTHORITY_MISSING_ROOT", Severity.ERROR)]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_GOVERNANCE_BREAKDOWN" not in codes


def test_governance_breakdown_triggered() -> None:
    findings = [
        _issue("AUTHORITY_MISSING_ROOT", Severity.ERROR),
        _issue("MISSING_REQUIRED_FIELD", Severity.ERROR),
    ]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_GOVERNANCE_BREAKDOWN" in codes


def test_governance_breakdown_priority_is_high() -> None:
    findings = [
        _issue("AUTHORITY_MISSING_ROOT", Severity.ERROR),
        _issue("MISSING_REQUIRED_FIELD", Severity.ERROR),
    ]
    insights = derive_insights(findings)
    insight = next(i for i in insights if i.code == "INSIGHT_GOVERNANCE_BREAKDOWN")
    assert insight.priority == "high"


# ---------------------------------------------------------------------------
# Pattern 4: Multiple documentation deficiencies per pipeline
# ---------------------------------------------------------------------------


def test_no_quality_gap_with_single_deficiency() -> None:
    findings = [_issue("AUDIT_MISSING_PURPOSE", pipeline_id="001")]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_CONTRACT_QUALITY_GAP" not in codes


def test_quality_gap_triggered_on_two_deficiencies() -> None:
    findings = [
        _issue("AUDIT_MISSING_PURPOSE", pipeline_id="001"),
        _issue("AUDIT_WEAK_SUCCESS_CRITERIA", pipeline_id="001"),
    ]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_CONTRACT_QUALITY_GAP" in codes


def test_quality_gap_requires_same_pipeline() -> None:
    findings = [
        _issue("AUDIT_MISSING_PURPOSE", pipeline_id="001"),
        _issue("AUDIT_WEAK_SUCCESS_CRITERIA", pipeline_id="002"),
    ]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_CONTRACT_QUALITY_GAP" not in codes


def test_quality_gap_priority_is_medium() -> None:
    findings = [
        _issue("AUDIT_MISSING_PURPOSE", pipeline_id="001"),
        _issue("AUDIT_MISSING_IMPL_NOTES", pipeline_id="001"),
    ]
    insights = derive_insights(findings)
    insight = next(i for i in insights if i.code == "INSIGHT_CONTRACT_QUALITY_GAP")
    assert insight.priority == "medium"


# ---------------------------------------------------------------------------
# Pattern 5: Dependency cycle + unresolved dependency
# ---------------------------------------------------------------------------


def test_graph_failure_requires_both_codes() -> None:
    findings = [_issue("DEPENDENCY_CYCLE", Severity.ERROR)]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_GRAPH_INTEGRITY_FAILURE" not in codes


def test_graph_failure_triggered() -> None:
    findings = [
        _issue("DEPENDENCY_CYCLE", Severity.ERROR),
        _issue("UNRESOLVED_DEPENDENCY", Severity.ERROR),
    ]
    insights = derive_insights(findings)
    codes = [i.code for i in insights]
    assert "INSIGHT_GRAPH_INTEGRITY_FAILURE" in codes


def test_graph_failure_priority_is_high() -> None:
    findings = [
        _issue("DEPENDENCY_CYCLE", Severity.ERROR),
        _issue("UNRESOLVED_DEPENDENCY", Severity.ERROR),
    ]
    insights = derive_insights(findings)
    insight = next(i for i in insights if i.code == "INSIGHT_GRAPH_INTEGRITY_FAILURE")
    assert insight.priority == "high"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_no_findings_produces_no_insights() -> None:
    insights = derive_insights([])
    assert insights == []


def test_multiple_patterns_can_trigger_simultaneously() -> None:
    """Verify that multiple patterns can fire in the same call."""
    findings = [
        _issue("AUDIT_UNCONTRACTED_SURFACE"),
        _issue("DEPENDENCY_CYCLE", Severity.ERROR),
        _issue("UNRESOLVED_DEPENDENCY", Severity.ERROR),
    ]
    insights = derive_insights(findings, candidate_count=2)
    codes = {i.code for i in insights}
    assert "INSIGHT_CANDIDATE_READY" in codes
    assert "INSIGHT_GRAPH_INTEGRITY_FAILURE" in codes


def test_all_insights_have_non_empty_explanation() -> None:
    findings = [
        _issue("AUDIT_UNCONTRACTED_SURFACE"),
        _issue("AUDIT_MISSING_OUTPUT", pipeline_id="001"),
        _issue("REGISTRY_STALE_ENTRY", pipeline_id="001"),
        _issue("AUTHORITY_MISSING_ROOT", Severity.ERROR),
        _issue("MISSING_REQUIRED_FIELD", Severity.ERROR),
        _issue("AUDIT_MISSING_PURPOSE", pipeline_id="002"),
        _issue("AUDIT_WEAK_SUCCESS_CRITERIA", pipeline_id="002"),
        _issue("DEPENDENCY_CYCLE", Severity.ERROR),
        _issue("UNRESOLVED_DEPENDENCY", Severity.ERROR),
    ]
    insights = derive_insights(findings, candidate_count=1)
    for insight in insights:
        assert len(insight.explanation) > 20, f"Short explanation in {insight.code}"
        assert insight.title, f"Empty title in {insight.code}"
        assert insight.related_findings, f"No related findings in {insight.code}"
