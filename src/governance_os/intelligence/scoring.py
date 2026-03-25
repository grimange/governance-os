"""Explainable governance scoring for governance-os.

Formula is intentionally simple and fully visible.
No hidden weights. No probabilistic inference.

Scoring rules
-------------
Per category:
  - Start at 100.
  - Deduct DEDUCTION_ERROR (25) per error finding.
  - Deduct DEDUCTION_WARNING (10) per warning finding.
  - INFO findings are not scored (informational only).
  - Floor at 0.

Overall score:
  - Mean of all category scores (rounded to nearest integer).

Grade bands:
  90–100 → A
  75–89  → B
  60–74  → C
  40–59  → D
  0–39   → F
"""

from __future__ import annotations

from governance_os.models.issue import Issue, Severity

DEDUCTION_ERROR: int = 25
DEDUCTION_WARNING: int = 10
MAX_SCORE: int = 100

FORMULA_EXPLANATION: str = (
    f"Per category: start={MAX_SCORE}, "
    f"error=-{DEDUCTION_ERROR} each, warning=-{DEDUCTION_WARNING} each, "
    "info=not scored, floor=0. "
    "Overall score = mean of all category scores (rounded)."
)

_GRADE_BANDS: list[tuple[int, str]] = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (0, "F"),
]


def grade(score: int) -> str:
    """Return the letter grade for *score*."""
    for threshold, letter in _GRADE_BANDS:
        if score >= threshold:
            return letter
    return "F"


def _score_issues(issues: list[Issue]) -> tuple[int, int, int, list[str]]:
    """Return (score, error_count, warning_count, deduction_descriptions)."""
    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)

    deductions: list[str] = []
    total_deduction = 0

    if errors:
        pts = errors * DEDUCTION_ERROR
        total_deduction += pts
        deductions.append(f"{errors} error(s) × {DEDUCTION_ERROR} = -{pts} pts")

    if warnings:
        pts = warnings * DEDUCTION_WARNING
        total_deduction += pts
        deductions.append(f"{warnings} warning(s) × {DEDUCTION_WARNING} = -{pts} pts")

    score = max(0, MAX_SCORE - total_deduction)
    return score, errors, warnings, deductions


def score_category(name: str, issues: list[Issue]) -> "CategoryScore":
    """Compute a CategoryScore for the given name and issue list."""
    from governance_os.models.score import CategoryScore

    score, errors, warnings, deductions = _score_issues(issues)
    infos = sum(1 for i in issues if i.severity == Severity.INFO)

    return CategoryScore(
        name=name,
        score=score,
        finding_count=len(issues),
        error_count=errors,
        warning_count=warnings,
        info_count=infos,
        deductions=deductions,
    )


def overall_score(categories: "list[CategoryScore]") -> int:  # type: ignore[name-defined]
    """Return the overall score as the mean of category scores."""
    if not categories:
        return MAX_SCORE
    return round(sum(c.score for c in categories) / len(categories))
