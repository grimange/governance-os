"""Tests for v0.8 pipeline lifecycle state inference."""

from pathlib import Path

import pytest

from governance_os.models.lifecycle import (
    LifecycleRecord,
    LifecycleResult,
    LifecycleState,
    VALID_DECLARED_STATES,
)
from governance_os.models.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Helpers — build minimal valid/invalid Pipeline fixtures
# ---------------------------------------------------------------------------


def _make_pipeline(
    tmp_path: Path,
    numeric_id: str = "001",
    slug: str = "test-pipeline",
    *,
    valid: bool = True,
    declared_state: str = "",
    depends_on: list[str] | None = None,
) -> Pipeline:
    """Create a Pipeline model written to tmp_path."""
    contract_path = tmp_path / "governance" / "pipelines" / f"{numeric_id}-{slug}.md"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    if valid:
        content = f"""# {numeric_id} — {slug.replace("-", " ").title()}

Stage: establish

Purpose:
Test pipeline.

Outputs:
- some-output

Success Criteria:
- criterion one
"""
    else:
        # Missing required fields → schema errors
        content = f"# {numeric_id} — {slug.replace('-', ' ').title()}\n"

    if declared_state:
        content += f"\nState: {declared_state}\n"

    contract_path.write_text(content, encoding="utf-8")

    return Pipeline(
        numeric_id=numeric_id,
        slug=slug,
        path=contract_path,
        title=slug.replace("-", " ").title() if valid else "",
        stage="establish" if valid else "",
        purpose="Test pipeline." if valid else "",
        outputs=["some-output"] if valid else [],
        success_criteria=["criterion one"] if valid else [],
        declared_state=declared_state,
        depends_on=depends_on or [],
    )


def _make_marker(root: Path, subdir: str, pipeline_id: str, content: str = "marker") -> None:
    marker_dir = root / "artifacts" / "governance" / subdir
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / f"{pipeline_id}.md").write_text(content, encoding="utf-8")


def _make_run_dir(root: Path, pipeline_id: str) -> None:
    run_dir = root / "artifacts" / "governance" / "runs" / pipeline_id
    run_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# LifecycleState enum
# ---------------------------------------------------------------------------


def test_lifecycle_state_has_all_seven_values():
    states = {s.value for s in LifecycleState}
    assert states == {"draft", "ready", "active", "blocked", "completed", "failed", "archived"}


def test_valid_declared_states_covers_all_values():
    assert VALID_DECLARED_STATES == {s.value for s in LifecycleState}


# ---------------------------------------------------------------------------
# LifecycleRecord model
# ---------------------------------------------------------------------------


def test_lifecycle_record_is_frozen(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    record = result.records[0]
    with pytest.raises(Exception):  # frozen model
        record.drift = not record.drift  # type: ignore[misc]


def test_lifecycle_record_fields_present(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    record = result.records[0]
    assert record.pipeline_id == "001"
    assert record.slug == "test-pipeline"
    assert isinstance(record.path, Path)
    assert isinstance(record.effective_state, LifecycleState)
    assert isinstance(record.drift, bool)
    assert isinstance(record.reasons, list)


# ---------------------------------------------------------------------------
# LifecycleResult model
# ---------------------------------------------------------------------------


def test_lifecycle_result_empty_pipelines(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    result = classify_lifecycle([], tmp_path)
    assert result.records == []


def test_lifecycle_result_by_state(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    ready = result.by_state(LifecycleState.READY)
    assert len(ready) == 1


def test_lifecycle_result_properties(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    # Should have either ready or draft, not failed/blocked
    assert isinstance(result.ready, list)
    assert isinstance(result.blocked, list)
    assert isinstance(result.failed, list)
    assert isinstance(result.completed, list)
    assert isinstance(result.draft, list)
    assert isinstance(result.active, list)
    assert isinstance(result.drifted, list)


# ---------------------------------------------------------------------------
# Inference: READY
# ---------------------------------------------------------------------------


def test_valid_pipeline_no_deps_is_ready(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.READY


def test_valid_pipeline_ready_has_empty_reasons(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].reasons == []


# ---------------------------------------------------------------------------
# Inference: DRAFT (schema errors)
# ---------------------------------------------------------------------------


def test_invalid_pipeline_is_draft(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=False)
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.DRAFT


def test_draft_pipeline_has_reason(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=False)
    result = classify_lifecycle([p], tmp_path)
    assert len(result.records[0].reasons) > 0


# ---------------------------------------------------------------------------
# Inference: FAILED (failure marker)
# ---------------------------------------------------------------------------


def test_failure_marker_makes_pipeline_failed(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    _make_marker(tmp_path, "failures", "001")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.FAILED


def test_failure_marker_reason_references_marker_path(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    _make_marker(tmp_path, "failures", "001")
    result = classify_lifecycle([p], tmp_path)
    assert any("failures/001" in r for r in result.records[0].reasons)


def test_failure_marker_overrides_declared_completed(tmp_path):
    """Failure marker takes priority over declared completed."""
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="completed")
    _make_marker(tmp_path, "failures", "001")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.FAILED


def test_failure_marker_only_for_matching_id(tmp_path):
    """Failure marker for 002 should not affect 001."""
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    _make_marker(tmp_path, "failures", "002")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.READY


# ---------------------------------------------------------------------------
# Inference: BLOCKED (block marker)
# ---------------------------------------------------------------------------


def test_block_marker_makes_pipeline_blocked(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    _make_marker(tmp_path, "blocks", "001")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.BLOCKED


def test_block_marker_reason_references_marker_path(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    _make_marker(tmp_path, "blocks", "001")
    result = classify_lifecycle([p], tmp_path)
    assert any("blocks/001" in r for r in result.records[0].reasons)


# ---------------------------------------------------------------------------
# Inference: ACTIVE (run dir marker)
# ---------------------------------------------------------------------------


def test_run_dir_makes_pipeline_active(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    _make_run_dir(tmp_path, "001")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.ACTIVE


def test_run_dir_reason_references_run_path(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    _make_run_dir(tmp_path, "001")
    result = classify_lifecycle([p], tmp_path)
    assert any("runs/001" in r for r in result.records[0].reasons)


def test_run_dir_does_not_activate_invalid_pipeline(tmp_path):
    """A pipeline with schema errors should remain DRAFT even with a run dir."""
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=False)
    _make_run_dir(tmp_path, "001")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.DRAFT


# ---------------------------------------------------------------------------
# Inference: COMPLETED (declared)
# ---------------------------------------------------------------------------


def test_declared_completed_is_completed(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="completed")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.COMPLETED


def test_declared_completed_has_reason(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="completed")
    result = classify_lifecycle([p], tmp_path)
    assert len(result.records[0].reasons) > 0


# ---------------------------------------------------------------------------
# Inference: ARCHIVED (declared)
# ---------------------------------------------------------------------------


def test_declared_archived_is_archived(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="archived")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.ARCHIVED


def test_archived_pipeline_has_no_drift(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="archived")
    result = classify_lifecycle([p], tmp_path)
    assert not result.records[0].drift


# ---------------------------------------------------------------------------
# Inference: BLOCKED (dependency propagation)
# ---------------------------------------------------------------------------


def test_pipeline_blocked_by_draft_dep(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    dep = _make_pipeline(tmp_path, "001", "dep-pipeline", valid=False)
    p = _make_pipeline(tmp_path, "002", "main-pipeline", valid=True, depends_on=["001"])
    result = classify_lifecycle([dep, p], tmp_path)

    main_record = next(r for r in result.records if r.pipeline_id == "002")
    assert main_record.effective_state == LifecycleState.BLOCKED


def test_pipeline_blocked_by_failed_dep(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    dep = _make_pipeline(tmp_path, "001", "dep-pipeline", valid=True)
    _make_marker(tmp_path, "failures", "001")
    p = _make_pipeline(tmp_path, "002", "main-pipeline", valid=True, depends_on=["001"])
    result = classify_lifecycle([dep, p], tmp_path)

    main_record = next(r for r in result.records if r.pipeline_id == "002")
    assert main_record.effective_state == LifecycleState.BLOCKED


def test_pipeline_ready_when_dep_completed(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    dep = _make_pipeline(tmp_path, "001", "dep-pipeline", valid=True, declared_state="completed")
    p = _make_pipeline(tmp_path, "002", "main-pipeline", valid=True, depends_on=["001"])
    result = classify_lifecycle([dep, p], tmp_path)

    main_record = next(r for r in result.records if r.pipeline_id == "002")
    assert main_record.effective_state == LifecycleState.READY


def test_dep_blockage_reason_mentions_dep(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    dep = _make_pipeline(tmp_path, "001", "dep-pipeline", valid=False)
    p = _make_pipeline(tmp_path, "002", "main-pipeline", valid=True, depends_on=["001"])
    result = classify_lifecycle([dep, p], tmp_path)

    main_record = next(r for r in result.records if r.pipeline_id == "002")
    assert any("001" in r for r in main_record.reasons)


def test_pipeline_ready_when_dep_active(tmp_path):
    """Active dep should not block downstream (it's progressing)."""
    from governance_os.lifecycle.core import classify_lifecycle

    dep = _make_pipeline(tmp_path, "001", "dep-pipeline", valid=True)
    _make_run_dir(tmp_path, "001")
    p = _make_pipeline(tmp_path, "002", "main-pipeline", valid=True, depends_on=["001"])
    result = classify_lifecycle([dep, p], tmp_path)

    main_record = next(r for r in result.records if r.pipeline_id == "002")
    # Active dep does NOT block downstream — it's only DRAFT/BLOCKED/FAILED that block
    assert main_record.effective_state == LifecycleState.READY


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


def test_no_declared_state_no_drift(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="")
    result = classify_lifecycle([p], tmp_path)
    assert not result.records[0].drift


def test_declared_matches_effective_no_drift(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="ready")
    result = classify_lifecycle([p], tmp_path)
    assert not result.records[0].drift


def test_declared_differs_from_effective_is_drift(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    # Valid pipeline → effective READY, but declare as "active"
    p = _make_pipeline(tmp_path, valid=True, declared_state="active")
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].drift


def test_unrecognised_declared_state_not_drift(tmp_path):
    """Unrecognised declared state is not counted as drift (it's a separate issue)."""
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="in-progress")
    result = classify_lifecycle([p], tmp_path)
    # "in-progress" is not in VALID_DECLARED_STATES → drift=False (not recognised)
    assert not result.records[0].drift


def test_drifted_list_contains_drifted_pipelines(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="active")
    result = classify_lifecycle([p], tmp_path)
    assert len(result.drifted) == 1


# ---------------------------------------------------------------------------
# lifecycle_issues() — derived Issue records
# ---------------------------------------------------------------------------


def test_lifecycle_issues_empty_on_clean(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle, lifecycle_issues

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    issues = lifecycle_issues(result)
    assert issues == []


def test_lifecycle_issues_drift_produces_warning(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle, lifecycle_issues
    from governance_os.models.issue import Severity

    p = _make_pipeline(tmp_path, valid=True, declared_state="active")
    result = classify_lifecycle([p], tmp_path)
    issues = lifecycle_issues(result)
    drift_issues = [i for i in issues if i.code == "LIFECYCLE_DRIFT"]
    assert len(drift_issues) == 1
    assert drift_issues[0].severity == Severity.WARNING


def test_lifecycle_issues_failed_produces_error(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle, lifecycle_issues
    from governance_os.models.issue import Severity

    p = _make_pipeline(tmp_path, valid=True)
    _make_marker(tmp_path, "failures", "001")
    result = classify_lifecycle([p], tmp_path)
    issues = lifecycle_issues(result)
    failed_issues = [i for i in issues if i.code == "LIFECYCLE_FAILED"]
    assert len(failed_issues) == 1
    assert failed_issues[0].severity == Severity.ERROR


def test_lifecycle_issues_invalid_declared_state_produces_warning(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle, lifecycle_issues
    from governance_os.models.issue import Severity

    p = _make_pipeline(tmp_path, valid=True, declared_state="in-progress")
    result = classify_lifecycle([p], tmp_path)
    issues = lifecycle_issues(result)
    bad_state_issues = [i for i in issues if i.code == "LIFECYCLE_INVALID_DECLARED_STATE"]
    assert len(bad_state_issues) == 1
    assert bad_state_issues[0].severity == Severity.WARNING


# ---------------------------------------------------------------------------
# Markdown parser — State: field
# ---------------------------------------------------------------------------


def test_parser_reads_state_field():
    from pathlib import Path
    from governance_os.parsing.markdown_contract import parse_contract

    source = """# 001 — Test Pipeline

Stage: establish

State: active

Purpose:
Test.

Outputs:
- output-file

Success Criteria:
- done
"""
    contract = parse_contract(Path("dummy.md"), source=source)
    assert contract.declared_state == "active"


def test_parser_reads_lifecycle_state_heading():
    from pathlib import Path
    from governance_os.parsing.markdown_contract import parse_contract

    source = """# 001 — Test Pipeline

Stage: establish

### Lifecycle State
completed

Purpose:
Test.

Outputs:
- output-file

Success Criteria:
- done
"""
    contract = parse_contract(Path("dummy.md"), source=source)
    assert contract.declared_state == "completed"


def test_parser_empty_declared_state_when_absent():
    from pathlib import Path
    from governance_os.parsing.markdown_contract import parse_contract

    source = """# 001 — Test Pipeline

Stage: establish

Purpose:
Test.

Outputs:
- output-file

Success Criteria:
- done
"""
    contract = parse_contract(Path("dummy.md"), source=source)
    assert contract.declared_state == ""


# ---------------------------------------------------------------------------
# Pipeline model — declared_state field
# ---------------------------------------------------------------------------


def test_pipeline_has_declared_state_field(tmp_path):
    p = _make_pipeline(tmp_path, valid=True)
    assert hasattr(p, "declared_state")
    assert p.declared_state == ""


def test_pipeline_declared_state_propagates_from_contract(tmp_path):
    from governance_os.api import scan as api_scan

    root = tmp_path
    pipelines_dir = root / "governance" / "pipelines"
    pipelines_dir.mkdir(parents=True)
    (pipelines_dir / "001--test-pipeline.md").write_text(
        """# 001 — Test Pipeline

Stage: establish

State: completed

Purpose:
Test.

Outputs:
- output

Success Criteria:
- done
""",
        encoding="utf-8",
    )
    (root / "governance.yaml").write_text(
        "profile: generic\npipelines_dir: governance/pipelines\n", encoding="utf-8"
    )

    result = api_scan(root)
    assert len(result.pipelines) == 1
    assert result.pipelines[0].declared_state == "completed"


# ---------------------------------------------------------------------------
# API — pipeline_lifecycle
# ---------------------------------------------------------------------------


def test_api_pipeline_lifecycle_returns_lifecycle_result(tmp_path):
    import governance_os.api as api

    result = api.pipeline_lifecycle(tmp_path)
    assert isinstance(result, LifecycleResult)


def test_api_pipeline_lifecycle_empty_repo(tmp_path):
    import governance_os.api as api

    result = api.pipeline_lifecycle(tmp_path)
    assert result.records == []


def test_api_pipeline_lifecycle_status_returns_none_for_unknown(tmp_path):
    import governance_os.api as api

    record = api.pipeline_lifecycle_status(tmp_path, "999")
    assert record is None


def test_api_pipeline_lifecycle_status_found_by_id(tmp_path):
    import governance_os.api as api

    root = tmp_path
    pipelines_dir = root / "governance" / "pipelines"
    pipelines_dir.mkdir(parents=True)
    (pipelines_dir / "001--found-pipeline.md").write_text(
        """# 001 — Found Pipeline

Stage: establish

Purpose:
Test.

Outputs:
- output

Success Criteria:
- done
""",
        encoding="utf-8",
    )
    (root / "governance.yaml").write_text(
        "profile: generic\npipelines_dir: governance/pipelines\n", encoding="utf-8"
    )

    record = api.pipeline_lifecycle_status(root, "001")
    assert record is not None
    assert record.pipeline_id == "001"


def test_api_pipeline_lifecycle_status_found_by_slug(tmp_path):
    import governance_os.api as api

    root = tmp_path
    pipelines_dir = root / "governance" / "pipelines"
    pipelines_dir.mkdir(parents=True)
    (pipelines_dir / "001--found-pipeline.md").write_text(
        """# 001 — Found Pipeline

Stage: establish

Purpose:
Test.

Outputs:
- output

Success Criteria:
- done
""",
        encoding="utf-8",
    )
    (root / "governance.yaml").write_text(
        "profile: generic\npipelines_dir: governance/pipelines\n", encoding="utf-8"
    )

    record = api.pipeline_lifecycle_status(root, "found-pipeline")
    assert record is not None
    assert record.slug == "found-pipeline"


# ---------------------------------------------------------------------------
# Marker file edge cases
# ---------------------------------------------------------------------------


def test_no_marker_dirs_does_not_error(tmp_path):
    """classify_lifecycle works even when artifacts/governance/ does not exist."""
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    # Do not create any marker dirs
    result = classify_lifecycle([p], tmp_path)
    assert result.records[0].effective_state == LifecycleState.READY


def test_block_marker_overrides_run_dir(tmp_path):
    """Block marker takes precedence over run directory."""
    from governance_os.lifecycle.core import classify_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    _make_marker(tmp_path, "blocks", "001")
    _make_run_dir(tmp_path, "001")
    result = classify_lifecycle([p], tmp_path)
    # Failure check first, then archived, then completed, then block — block wins over run
    assert result.records[0].effective_state == LifecycleState.BLOCKED


def test_multiple_pipelines_independent_markers(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle

    p1 = _make_pipeline(tmp_path, "001", "first-pipeline", valid=True)
    p2 = _make_pipeline(tmp_path, "002", "second-pipeline", valid=True)
    _make_marker(tmp_path, "failures", "001")
    result = classify_lifecycle([p1, p2], tmp_path)

    r1 = next(r for r in result.records if r.pipeline_id == "001")
    r2 = next(r for r in result.records if r.pipeline_id == "002")
    assert r1.effective_state == LifecycleState.FAILED
    assert r2.effective_state == LifecycleState.READY


# ---------------------------------------------------------------------------
# Console formatting
# ---------------------------------------------------------------------------


def test_format_lifecycle_empty_result(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle
    from governance_os.reporting.console import format_lifecycle

    result = classify_lifecycle([], tmp_path)
    output = format_lifecycle(result)
    assert "No pipelines" in output


def test_format_lifecycle_shows_state(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle
    from governance_os.reporting.console import format_lifecycle

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    output = format_lifecycle(result)
    assert "ready" in output


def test_format_lifecycle_shows_drift_marker(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle
    from governance_os.reporting.console import format_lifecycle

    p = _make_pipeline(tmp_path, valid=True, declared_state="active")
    result = classify_lifecycle([p], tmp_path)
    output = format_lifecycle(result)
    assert "DRIFT" in output


def test_format_lifecycle_record(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle
    from governance_os.reporting.console import format_lifecycle_record

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    output = format_lifecycle_record(result.records[0])
    assert "001" in output
    assert "ready" in output


# ---------------------------------------------------------------------------
# JSON reporting
# ---------------------------------------------------------------------------


def test_lifecycle_to_json_structure(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle
    from governance_os.reporting.json_report import lifecycle_to_json

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    data = lifecycle_to_json(result)
    assert "records" in data
    assert "drift_count" in data
    assert data["record_count"] == 1


def test_lifecycle_record_to_json_structure(tmp_path):
    from governance_os.lifecycle.core import classify_lifecycle
    from governance_os.reporting.json_report import lifecycle_record_to_json

    p = _make_pipeline(tmp_path, valid=True)
    result = classify_lifecycle([p], tmp_path)
    data = lifecycle_record_to_json(result.records[0])
    assert "pipeline_id" in data
    assert "effective_state" in data
    assert "declared_state" in data
    assert "drift" in data
    assert "reasons" in data
