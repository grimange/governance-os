"""Tests for governance_os.validation.schema and integrity."""

from pathlib import Path

import pytest

from governance_os.models.issue import Severity
from governance_os.models.pipeline import Pipeline
from governance_os.validation.integrity import validate_integrity
from governance_os.validation.schema import ALLOWED_STAGES, validate_pipeline, validate_pipelines


def _valid(id_="001", slug="foo", stage="establish"):
    return Pipeline(
        numeric_id=id_,
        slug=slug,
        path=Path(f"{id_}--{slug}.md"),
        title="Title",
        stage=stage,
        purpose="Does stuff.",
        outputs=["artifacts/out.json"],
        success_criteria=["works"],
    )


# --- schema ---


def test_valid_pipeline_has_no_issues():
    assert validate_pipeline(_valid()) == []


def test_missing_title():
    p = Pipeline(
        numeric_id="001",
        slug="x",
        path=Path("001--x.md"),
        stage="establish",
        purpose="x",
        outputs=["y"],
        success_criteria=["z"],
    )
    codes = [i.code for i in validate_pipeline(p)]
    assert "MISSING_REQUIRED_FIELD" in codes


def test_missing_stage():
    p = Pipeline(
        numeric_id="001",
        slug="x",
        path=Path("001--x.md"),
        title="T",
        purpose="x",
        outputs=["y"],
        success_criteria=["z"],
    )
    codes = [i.code for i in validate_pipeline(p)]
    assert "MISSING_REQUIRED_FIELD" in codes


def test_missing_purpose():
    p = Pipeline(
        numeric_id="001",
        slug="x",
        path=Path("001--x.md"),
        title="T",
        stage="establish",
        outputs=["y"],
        success_criteria=["z"],
    )
    codes = [i.code for i in validate_pipeline(p)]
    assert "MISSING_REQUIRED_FIELD" in codes


def test_missing_outputs():
    p = Pipeline(
        numeric_id="001",
        slug="x",
        path=Path("001--x.md"),
        title="T",
        stage="establish",
        purpose="x",
        success_criteria=["z"],
    )
    codes = [i.code for i in validate_pipeline(p)]
    assert "MISSING_REQUIRED_FIELD" in codes


def test_missing_success_criteria():
    p = Pipeline(
        numeric_id="001",
        slug="x",
        path=Path("001--x.md"),
        title="T",
        stage="establish",
        purpose="x",
        outputs=["y"],
    )
    codes = [i.code for i in validate_pipeline(p)]
    assert "MISSING_REQUIRED_FIELD" in codes


@pytest.mark.parametrize("stage", sorted(ALLOWED_STAGES))
def test_all_allowed_stages_pass(stage):
    p = _valid(stage=stage)
    issues = validate_pipeline(p)
    assert not any(i.code == "INVALID_STAGE" for i in issues)


def test_invalid_stage():
    p = _valid()
    p = p.model_copy(update={"stage": "bogus"})
    codes = [i.code for i in validate_pipeline(p)]
    assert "INVALID_STAGE" in codes


def test_invalid_stage_is_error():
    p = _valid()
    p = p.model_copy(update={"stage": "bogus"})
    issues = validate_pipeline(p)
    stage_issues = [i for i in issues if i.code == "INVALID_STAGE"]
    assert all(i.severity == Severity.ERROR for i in stage_issues)


def test_duplicate_output_entry():
    p = _valid()
    p = p.model_copy(update={"outputs": ["artifact", "artifact"]})
    codes = [i.code for i in validate_pipeline(p)]
    assert "DUPLICATE_LIST_ENTRY" in codes


def test_duplicate_dep_entry():
    p = _valid()
    p = p.model_copy(update={"depends_on": ["001", "001"]})
    codes = [i.code for i in validate_pipeline(p)]
    assert "DUPLICATE_LIST_ENTRY" in codes


def test_validate_pipelines_aggregates():
    pipelines = [_valid("001", "a"), _valid("002", "b")]
    issues = validate_pipelines(pipelines)
    assert issues == []


# --- integrity ---


def test_no_integrity_issues_for_unique_pipelines():
    pipelines = [_valid("001", "alpha"), _valid("002", "beta")]
    assert validate_integrity(pipelines) == []


def test_duplicate_id_detected():
    pipelines = [
        Pipeline(numeric_id="001", slug="a", path=Path("001--a.md")),
        Pipeline(numeric_id="001", slug="b", path=Path("001--b.md")),
    ]
    codes = [i.code for i in validate_integrity(pipelines)]
    assert "DUPLICATE_PIPELINE_ID" in codes


def test_duplicate_id_is_error():
    pipelines = [
        Pipeline(numeric_id="001", slug="a", path=Path("001--a.md")),
        Pipeline(numeric_id="001", slug="b", path=Path("001--b.md")),
    ]
    issues = validate_integrity(pipelines)
    dup = [i for i in issues if i.code == "DUPLICATE_PIPELINE_ID"]
    assert all(i.severity == Severity.ERROR for i in dup)


def test_duplicate_slug_detected():
    pipelines = [
        Pipeline(numeric_id="001", slug="foo", path=Path("001--foo.md")),
        Pipeline(numeric_id="002", slug="foo", path=Path("002--foo.md")),
    ]
    codes = [i.code for i in validate_integrity(pipelines)]
    assert "DUPLICATE_SLUG" in codes


def test_duplicate_slug_is_warning():
    pipelines = [
        Pipeline(numeric_id="001", slug="foo", path=Path("001--foo.md")),
        Pipeline(numeric_id="002", slug="foo", path=Path("002--foo.md")),
    ]
    issues = validate_integrity(pipelines)
    slug_issues = [i for i in issues if i.code == "DUPLICATE_SLUG"]
    assert all(i.severity == Severity.WARNING for i in slug_issues)


def test_empty_pipeline_list_has_no_integrity_issues():
    assert validate_integrity([]) == []
