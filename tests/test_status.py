"""Tests for governance_os.validation.status_logic."""

from pathlib import Path

from governance_os.models.pipeline import Pipeline
from governance_os.models.status import PipelineStatus
from governance_os.validation.status_logic import classify


def _valid(id_, slug, deps=None):
    return Pipeline(
        numeric_id=id_,
        slug=slug,
        path=Path(f"pipelines/{id_}--{slug}.md"),
        depends_on=deps or [],
        title="T",
        stage="establish",
        purpose="P",
        outputs=["artifact"],
        success_criteria=["ok"],
    )


def _invalid(id_, slug):
    return Pipeline(numeric_id=id_, slug=slug, path=Path(f"pipelines/{id_}--{slug}.md"))


def test_single_valid_no_deps_is_orphaned():
    result = classify([_valid("001", "solo")])
    assert result.records[0].status == PipelineStatus.ORPHANED


def test_two_valid_with_dep_both_ready():
    result = classify([_valid("001", "a"), _valid("002", "b", ["001"])])
    by_id = {r.pipeline_id: r for r in result.records}
    assert by_id["001"].status == PipelineStatus.READY
    assert by_id["002"].status == PipelineStatus.READY


def test_invalid_pipeline_classified_invalid():
    result = classify([_invalid("001", "bad")])
    assert result.records[0].status == PipelineStatus.INVALID


def test_blocked_by_invalid_prerequisite():
    pipelines = [_invalid("001", "bad"), _valid("002", "good", ["001"])]
    result = classify(pipelines)
    by_id = {r.pipeline_id: r for r in result.records}
    assert by_id["001"].status == PipelineStatus.INVALID
    assert by_id["002"].status == PipelineStatus.BLOCKED


def test_blocked_propagates_through_chain():
    pipelines = [
        _invalid("001", "bad"),
        _valid("002", "mid", ["001"]),
        _valid("003", "end", ["002"]),
    ]
    result = classify(pipelines)
    by_id = {r.pipeline_id: r for r in result.records}
    assert by_id["002"].status == PipelineStatus.BLOCKED
    assert by_id["003"].status == PipelineStatus.BLOCKED


def test_blocked_by_unresolved_dep():
    result = classify([_valid("001", "x", ["999"])])
    assert result.records[0].status == PipelineStatus.BLOCKED


def test_blocked_by_cycle():
    pipelines = [_valid("001", "a", ["002"]), _valid("002", "b", ["001"])]
    result = classify(pipelines)
    statuses = {r.status for r in result.records}
    assert PipelineStatus.BLOCKED in statuses


def test_status_result_helpers():
    pipelines = [
        _invalid("001", "bad"),
        _valid("002", "a"),
        _valid("003", "b", ["002"]),
    ]
    result = classify(pipelines)
    assert len(result.invalid) == 1
    assert result.invalid[0].pipeline_id == "001"
    assert len(result.ready) >= 1


def test_empty_pipeline_list():
    result = classify([])
    assert result.records == []


def test_blocked_reasons_non_empty():
    pipelines = [_invalid("001", "bad"), _valid("002", "good", ["001"])]
    result = classify(pipelines)
    by_id = {r.pipeline_id: r for r in result.records}
    assert by_id["002"].reasons
