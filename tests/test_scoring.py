"""Tests for the governance scoring module."""

import pytest

from governance_os.intelligence.scoring import (
    DEDUCTION_ERROR,
    DEDUCTION_WARNING,
    FORMULA_EXPLANATION,
    grade,
    overall_score,
    score_category,
)
from governance_os.models.issue import Issue, Severity
from governance_os.models.score import CategoryScore


def _error(code: str = "X") -> Issue:
    return Issue(code=code, severity=Severity.ERROR, message="err")


def _warning(code: str = "X") -> Issue:
    return Issue(code=code, severity=Severity.WARNING, message="warn")


def _info(code: str = "X") -> Issue:
    return Issue(code=code, severity=Severity.INFO, message="info")


# ---------------------------------------------------------------------------
# score_category — basic deduction
# ---------------------------------------------------------------------------


def test_no_issues_scores_100() -> None:
    cat = score_category("integrity", [])
    assert cat.score == 100
    assert cat.finding_count == 0
    assert cat.error_count == 0
    assert cat.warning_count == 0
    assert cat.info_count == 0
    assert cat.deductions == []


def test_one_error_deducts_correctly() -> None:
    cat = score_category("integrity", [_error()])
    assert cat.score == 100 - DEDUCTION_ERROR
    assert cat.error_count == 1


def test_one_warning_deducts_correctly() -> None:
    cat = score_category("readiness", [_warning()])
    assert cat.score == 100 - DEDUCTION_WARNING
    assert cat.warning_count == 1


def test_info_not_scored() -> None:
    """INFO findings must not affect the score."""
    cat = score_category("coverage", [_info()])
    assert cat.score == 100
    assert cat.info_count == 1
    assert cat.deductions == []


def test_mixed_findings_combined_deduction() -> None:
    issues = [_error(), _warning(), _info()]
    cat = score_category("drift", issues)
    expected = 100 - DEDUCTION_ERROR - DEDUCTION_WARNING
    assert cat.score == expected
    assert cat.finding_count == 3
    assert cat.error_count == 1
    assert cat.warning_count == 1
    assert cat.info_count == 1


def test_floor_at_zero() -> None:
    """More errors than can be absorbed must floor at 0, not go negative."""
    issues = [_error() for _ in range(10)]
    cat = score_category("integrity", issues)
    assert cat.score == 0


def test_deductions_are_listed() -> None:
    cat = score_category("authority", [_error(), _error(), _warning()])
    assert len(cat.deductions) == 2  # one line for errors, one for warnings
    assert "error" in cat.deductions[0]
    assert "warning" in cat.deductions[1]


def test_category_name_preserved() -> None:
    cat = score_category("my-category", [])
    assert cat.name == "my-category"


# ---------------------------------------------------------------------------
# overall_score
# ---------------------------------------------------------------------------


def test_overall_score_empty_returns_100() -> None:
    assert overall_score([]) == 100


def test_overall_score_mean_of_categories() -> None:
    cats = [
        CategoryScore(name="a", score=80, finding_count=0, error_count=0, warning_count=0, info_count=0, deductions=[]),
        CategoryScore(name="b", score=60, finding_count=0, error_count=0, warning_count=0, info_count=0, deductions=[]),
    ]
    assert overall_score(cats) == 70


def test_overall_score_rounds_correctly() -> None:
    cats = [
        CategoryScore(name="a", score=90, finding_count=0, error_count=0, warning_count=0, info_count=0, deductions=[]),
        CategoryScore(name="b", score=91, finding_count=0, error_count=0, warning_count=0, info_count=0, deductions=[]),
        CategoryScore(name="c", score=92, finding_count=0, error_count=0, warning_count=0, info_count=0, deductions=[]),
    ]
    # mean = 91.0
    assert overall_score(cats) == 91


# ---------------------------------------------------------------------------
# grade
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "score_val,expected_grade",
    [
        (100, "A"),
        (90, "A"),
        (89, "B"),
        (75, "B"),
        (74, "C"),
        (60, "C"),
        (59, "D"),
        (40, "D"),
        (39, "F"),
        (0, "F"),
    ],
)
def test_grade_bands(score_val: int, expected_grade: str) -> None:
    assert grade(score_val) == expected_grade


# ---------------------------------------------------------------------------
# formula_explanation
# ---------------------------------------------------------------------------


def test_formula_explanation_non_empty() -> None:
    assert len(FORMULA_EXPLANATION) > 10
    assert "error" in FORMULA_EXPLANATION
    assert "warning" in FORMULA_EXPLANATION
