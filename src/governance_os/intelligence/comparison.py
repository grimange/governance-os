"""Trend comparison support for governance-os.

Compares a current ScoreResult against a previously saved score JSON report.
Produces a list of ScoreDelta objects describing what changed.

Constraints:
  - File-based only. No history tracking system.
  - The previous file must be a JSON report produced by `govos score --json`.
  - Missing categories in the previous report default to 100 (no issues).
"""

from __future__ import annotations

import json
from pathlib import Path

from governance_os.models.score import ScoreDelta


def load_previous_scores(path: Path) -> tuple[int | None, dict[str, int]]:
    """Load overall and per-category scores from a previous score JSON report.

    Args:
        path: Path to the previous JSON report file.

    Returns:
        (overall_score, {category_name: score}) or (None, {}) on failure.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, {}

    if data.get("command") != "score":
        # Not a score report — return empty to avoid misleading deltas.
        return None, {}

    overall = data.get("overall_score")
    categories = {c["name"]: c["score"] for c in data.get("categories", [])}
    return overall, categories


def compute_deltas(
    current_overall: int,
    current_categories: "list[CategoryScore]",  # type: ignore[name-defined]
    compare_path: Path,
) -> list[ScoreDelta]:
    """Compare current scores against a previous report file.

    Args:
        current_overall: Overall score from the current run.
        current_categories: Category scores from the current run.
        compare_path: Path to the previous score JSON report.

    Returns:
        List of ScoreDelta records for categories (and overall) that changed.
        Returns empty list if the previous file cannot be read or is not a score report.
    """
    prev_overall, prev_cats = load_previous_scores(compare_path)
    if prev_overall is None and not prev_cats:
        return []

    deltas: list[ScoreDelta] = []

    # Overall score delta
    if prev_overall is not None and prev_overall != current_overall:
        deltas.append(
            ScoreDelta(
                category="overall",
                previous_score=prev_overall,
                current_score=current_overall,
                change=current_overall - prev_overall,
            )
        )

    # Per-category deltas
    current_cat_map = {c.name: c.score for c in current_categories}
    all_names = sorted(set(current_cat_map) | set(prev_cats))

    for name in all_names:
        prev = prev_cats.get(name, 100)
        curr = current_cat_map.get(name, 100)
        if prev != curr:
            deltas.append(
                ScoreDelta(
                    category=name,
                    previous_score=prev,
                    current_score=curr,
                    change=curr - prev,
                )
            )

    return deltas
