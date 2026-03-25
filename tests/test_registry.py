"""Tests for the pipeline registry module."""

import json
from pathlib import Path

from governance_os.models.pipeline import Pipeline
from governance_os.registry.core import (
    build_registry,
    reconcile_registry,
)


def _make_pipeline(
    num_id: str, slug: str, stage: str = "establish", outputs: list | None = None
) -> Pipeline:
    return Pipeline(
        numeric_id=num_id,
        slug=slug,
        path=Path(f"governance/pipelines/{num_id}--{slug}.md"),
        title=f"Pipeline {num_id}",
        stage=stage,
        purpose="Test pipeline",
        outputs=outputs if outputs is not None else ["artifacts/out.json"],
        success_criteria=["Done"],
    )


def test_build_registry_empty(tmp_path):
    result = build_registry(tmp_path, [])
    assert result.entry_count == 0
    assert result.passed


def test_build_registry_single(tmp_path):
    p = _make_pipeline("001", "setup")
    result = build_registry(tmp_path, [p])
    assert result.entry_count == 1
    assert result.entries[0].pipeline_id == "001"
    assert result.entries[0].slug == "setup"
    assert result.entries[0].stage == "establish"
    assert result.entries[0].outputs_count == 1
    assert result.passed


def test_build_registry_multiple_sorted(tmp_path):
    p1 = _make_pipeline("002", "b-pipeline")
    p2 = _make_pipeline("001", "a-pipeline")
    result = build_registry(tmp_path, [p1, p2])
    assert result.entry_count == 2
    # Should be sorted by numeric_id
    assert result.entries[0].pipeline_id == "001"
    assert result.entries[1].pipeline_id == "002"


def test_build_registry_duplicate_id(tmp_path):
    p1 = _make_pipeline("001", "setup")
    p2 = _make_pipeline("001", "setup-duplicate")
    result = build_registry(tmp_path, [p1, p2])
    error_codes = [i.code for i in result.issues if i.severity.value == "error"]
    assert "REGISTRY_DUPLICATE_ID" in error_codes
    assert not result.passed


def test_build_registry_missing_stage(tmp_path):
    p = _make_pipeline("001", "setup", stage="")
    result = build_registry(tmp_path, [p])
    warning_codes = [i.code for i in result.issues if i.severity.value == "warning"]
    assert "REGISTRY_MISSING_STAGE" in warning_codes


def test_build_registry_no_outputs(tmp_path):
    p = _make_pipeline("001", "setup", outputs=[])
    result = build_registry(tmp_path, [p])
    warning_codes = [i.code for i in result.issues if i.severity.value == "warning"]
    assert "REGISTRY_NO_OUTPUTS" in warning_codes


def test_reconcile_registry_missing_file(tmp_path):
    p = _make_pipeline("001", "setup")
    snapshot_path = tmp_path / "registry.json"
    result = reconcile_registry(tmp_path, [p], snapshot_path)
    warning_codes = [i.code for i in result.issues]
    assert "REGISTRY_FILE_MISSING" in warning_codes


def test_reconcile_registry_matches(tmp_path):
    p = _make_pipeline("001", "setup")
    snapshot = {
        "entries": [{"pipeline_id": "001", "slug": "setup"}],
    }
    snapshot_path = tmp_path / "registry.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    result = reconcile_registry(tmp_path, [p], snapshot_path)
    # No stale or untracked entries
    recon_codes = [
        i.code
        for i in result.issues
        if i.code in ("REGISTRY_STALE_ENTRY", "REGISTRY_UNTRACKED_PIPELINE")
    ]
    assert recon_codes == []


def test_reconcile_registry_stale_entry(tmp_path):
    p = _make_pipeline("001", "setup")
    snapshot = {
        "entries": [
            {"pipeline_id": "001", "slug": "setup"},
            {"pipeline_id": "002", "slug": "old-pipeline"},  # stale
        ],
    }
    snapshot_path = tmp_path / "registry.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    result = reconcile_registry(tmp_path, [p], snapshot_path)
    codes = [i.code for i in result.issues]
    assert "REGISTRY_STALE_ENTRY" in codes


def test_reconcile_registry_untracked(tmp_path):
    p1 = _make_pipeline("001", "setup")
    p2 = _make_pipeline("002", "new-pipeline")  # not in snapshot
    snapshot = {"entries": [{"pipeline_id": "001", "slug": "setup"}]}
    snapshot_path = tmp_path / "registry.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    result = reconcile_registry(tmp_path, [p1, p2], snapshot_path)
    codes = [i.code for i in result.issues]
    assert "REGISTRY_UNTRACKED_PIPELINE" in codes


def test_reconcile_registry_invalid_json(tmp_path):
    p = _make_pipeline("001", "setup")
    snapshot_path = tmp_path / "registry.json"
    snapshot_path.write_text("not valid json {{}", encoding="utf-8")
    result = reconcile_registry(tmp_path, [p], snapshot_path)
    codes = [i.code for i in result.issues]
    assert "REGISTRY_FILE_INVALID" in codes
