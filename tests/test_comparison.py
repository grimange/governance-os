"""Tests for the score comparison / delta module."""

import json
from pathlib import Path

import pytest

from governance_os.intelligence.comparison import compute_deltas, load_previous_scores
from governance_os.models.score import CategoryScore


def _cat(name: str, score: int) -> CategoryScore:
    return CategoryScore(
        name=name,
        score=score,
        finding_count=0,
        error_count=0,
        warning_count=0,
        info_count=0,
        deductions=[],
    )


def _write_score_report(path: Path, overall: int, categories: list[dict]) -> Path:
    data = {
        "command": "score",
        "overall_score": overall,
        "categories": categories,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_previous_scores
# ---------------------------------------------------------------------------


def test_load_previous_scores_valid(tmp_path: Path) -> None:
    report = tmp_path / "prev.json"
    _write_score_report(
        report,
        overall=72,
        categories=[{"name": "integrity", "score": 50}, {"name": "drift", "score": 80}],
    )
    overall, cats = load_previous_scores(report)
    assert overall == 72
    assert cats == {"integrity": 50, "drift": 80}


def test_load_previous_scores_missing_file(tmp_path: Path) -> None:
    overall, cats = load_previous_scores(tmp_path / "nonexistent.json")
    assert overall is None
    assert cats == {}


def test_load_previous_scores_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    overall, cats = load_previous_scores(bad)
    assert overall is None
    assert cats == {}


def test_load_previous_scores_wrong_command(tmp_path: Path) -> None:
    report = tmp_path / "other.json"
    report.write_text(json.dumps({"command": "verify", "overall_score": 90}), encoding="utf-8")
    overall, cats = load_previous_scores(report)
    assert overall is None
    assert cats == {}


# ---------------------------------------------------------------------------
# compute_deltas
# ---------------------------------------------------------------------------


def test_no_deltas_when_scores_unchanged(tmp_path: Path) -> None:
    report = tmp_path / "prev.json"
    _write_score_report(
        report,
        overall=80,
        categories=[{"name": "integrity", "score": 80}],
    )
    cats = [_cat("integrity", 80)]
    deltas = compute_deltas(80, cats, report)
    assert deltas == []


def test_overall_delta_detected(tmp_path: Path) -> None:
    report = tmp_path / "prev.json"
    _write_score_report(report, overall=60, categories=[])
    deltas = compute_deltas(80, [], report)
    assert len(deltas) == 1
    d = deltas[0]
    assert d.category == "overall"
    assert d.previous_score == 60
    assert d.current_score == 80
    assert d.change == 20


def test_category_delta_positive(tmp_path: Path) -> None:
    report = tmp_path / "prev.json"
    _write_score_report(
        report,
        overall=70,
        categories=[{"name": "integrity", "score": 50}],
    )
    cats = [_cat("integrity", 80)]
    deltas = compute_deltas(70, cats, report)
    cat_delta = next(d for d in deltas if d.category == "integrity")
    assert cat_delta.change == 30  # 80 - 50
    assert cat_delta.current_score == 80
    assert cat_delta.previous_score == 50


def test_category_delta_negative(tmp_path: Path) -> None:
    report = tmp_path / "prev.json"
    _write_score_report(
        report,
        overall=90,
        categories=[{"name": "drift", "score": 100}],
    )
    cats = [_cat("drift", 65)]
    deltas = compute_deltas(65, cats, report)
    cat_delta = next(d for d in deltas if d.category == "drift")
    assert cat_delta.change == -35


def test_new_category_defaults_previous_to_100(tmp_path: Path) -> None:
    """A category not in the previous report defaults previous score to 100."""
    report = tmp_path / "prev.json"
    _write_score_report(report, overall=100, categories=[])
    cats = [_cat("authority", 70)]
    deltas = compute_deltas(70, cats, report)
    cat_delta = next((d for d in deltas if d.category == "authority"), None)
    assert cat_delta is not None
    assert cat_delta.previous_score == 100
    assert cat_delta.change == -30


def test_missing_compare_file_returns_empty(tmp_path: Path) -> None:
    deltas = compute_deltas(80, [_cat("integrity", 80)], tmp_path / "missing.json")
    assert deltas == []


def test_multiple_categories_with_mixed_changes(tmp_path: Path) -> None:
    report = tmp_path / "prev.json"
    _write_score_report(
        report,
        overall=70,
        categories=[
            {"name": "integrity", "score": 80},
            {"name": "drift", "score": 60},
        ],
    )
    cats = [_cat("integrity", 80), _cat("drift", 90)]  # drift improved, integrity unchanged
    deltas = compute_deltas(85, cats, report)

    categories_changed = {d.category for d in deltas}
    assert "drift" in categories_changed
    assert "integrity" not in categories_changed  # unchanged — no delta
