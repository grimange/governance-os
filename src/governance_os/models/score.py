"""Score result models for governance-os v0.4 intelligence layer."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from governance_os.models.issue import Issue


class CategoryScore(BaseModel):
    """Score and finding breakdown for a single governance category."""

    name: str
    score: int  # 0–100
    finding_count: int
    error_count: int
    warning_count: int
    info_count: int
    deductions: list[str]  # human-readable deduction lines


class DerivedInsight(BaseModel):
    """A cross-signal insight derived from combinations of findings."""

    code: str
    title: str
    explanation: str
    priority: str  # "high" | "medium" | "low"
    related_findings: list[str]  # issue codes that triggered this insight


class ScoreDelta(BaseModel):
    """Score change for one category between the current and a previous run."""

    category: str
    previous_score: int
    current_score: int
    change: int  # positive = improvement, negative = regression


class PrioritizedFinding(BaseModel):
    """An Issue decorated with its computed priority level."""

    priority: str  # "high" | "medium" | "low"
    code: str
    severity: str
    message: str
    path: str | None
    pipeline_id: str | None
    suggestion: str | None

    @classmethod
    def from_issue(cls, priority: str, issue: Issue) -> "PrioritizedFinding":
        return cls(
            priority=priority,
            code=issue.code,
            severity=issue.severity.value,
            message=issue.message,
            path=str(issue.path) if issue.path else None,
            pipeline_id=issue.pipeline_id,
            suggestion=issue.suggestion,
        )


class ScoreResult(BaseModel):
    """Full result of the `govos score` command."""

    root: Path
    overall_score: int  # 0–100
    grade: str  # A / B / C / D / F
    categories: list[CategoryScore]
    prioritized_findings: list[PrioritizedFinding]
    derived_insights: list[DerivedInsight]
    delta: list[ScoreDelta]  # empty when no comparison
    formula_explanation: str

    model_config = {"frozen": False}
