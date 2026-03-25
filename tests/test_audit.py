"""Tests for the governance audit module."""

from pathlib import Path

from governance_os.audit.core import audit_coverage, audit_drift, audit_readiness
from governance_os.models.pipeline import Pipeline


def _make_pipeline(
    num_id: str = "001",
    slug: str = "setup",
    stage: str = "establish",
    purpose: str = "Test.",
    scope: str = "test",
    outputs: list | None = None,
    success_criteria: list | None = None,
    implementation_notes: str = "How to run.",
) -> Pipeline:
    return Pipeline(
        numeric_id=num_id,
        slug=slug,
        path=Path(f"governance/pipelines/{num_id}--{slug}.md"),
        title=f"Pipeline {num_id}",
        stage=stage,
        scope=scope,
        purpose=purpose,
        outputs=outputs if outputs is not None else ["artifacts/out.json"],
        success_criteria=success_criteria if success_criteria is not None else ["Done"],
        implementation_notes=implementation_notes,
    )


# ---------------------------------------------------------------------------
# audit_readiness
# ---------------------------------------------------------------------------


def test_audit_readiness_no_pipelines(tmp_path):
    result = audit_readiness(tmp_path, [])
    codes = [f.code for f in result.findings]
    assert "AUDIT_NO_PIPELINES" in codes


def test_audit_readiness_clean(tmp_path):
    p = _make_pipeline(purpose="Does things.", scope="repo")
    result = audit_readiness(tmp_path, [p])
    error_codes = [f.code for f in result.findings if f.severity.value == "error"]
    assert not error_codes


def test_audit_readiness_missing_purpose(tmp_path):
    p = _make_pipeline(purpose="")
    result = audit_readiness(tmp_path, [p])
    codes = [f.code for f in result.findings]
    assert "AUDIT_MISSING_PURPOSE" in codes


def test_audit_readiness_missing_scope(tmp_path):
    p = _make_pipeline(scope="")
    result = audit_readiness(tmp_path, [p])
    codes = [f.code for f in result.findings]
    assert "AUDIT_MISSING_SCOPE" in codes


def test_audit_readiness_missing_impl_notes(tmp_path):
    p = _make_pipeline(implementation_notes="")
    result = audit_readiness(tmp_path, [p])
    codes = [f.code for f in result.findings]
    assert "AUDIT_MISSING_IMPL_NOTES" in codes


def test_audit_readiness_weak_success_criteria(tmp_path):
    p = _make_pipeline(success_criteria=["Just one criterion"])
    result = audit_readiness(tmp_path, [p])
    codes = [f.code for f in result.findings]
    assert "AUDIT_WEAK_SUCCESS_CRITERIA" in codes


def test_audit_readiness_mode(tmp_path):
    p = _make_pipeline()
    result = audit_readiness(tmp_path, [p])
    assert result.mode == "readiness"


# ---------------------------------------------------------------------------
# audit_coverage
# ---------------------------------------------------------------------------


def test_audit_coverage_no_surfaces(tmp_path):
    result = audit_coverage(tmp_path, [], tmp_path / "governance" / "pipelines")
    codes = [f.code for f in result.findings]
    assert "AUDIT_NO_SURFACES_FOUND" in codes


def test_audit_coverage_detects_makefile(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "Makefile").touch()
    result = audit_coverage(tmp_path, [], tmp_path / "governance" / "pipelines")
    codes = [f.code for f in result.findings]
    assert "AUDIT_UNCONTRACTED_SURFACE" in codes


def test_audit_coverage_contracted_surface_excluded(tmp_path):
    # If directory slug is already contracted, it should not appear
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "Makefile").touch()
    p = _make_pipeline(slug="scripts")
    result = audit_coverage(tmp_path, [p], tmp_path / "governance" / "pipelines")
    codes = [f.code for f in result.findings]
    assert "AUDIT_UNCONTRACTED_SURFACE" not in codes


def test_audit_coverage_mode(tmp_path):
    result = audit_coverage(tmp_path, [], tmp_path / "governance" / "pipelines")
    assert result.mode == "coverage"


# ---------------------------------------------------------------------------
# audit_drift
# ---------------------------------------------------------------------------


def test_audit_drift_no_missing_outputs(tmp_path):
    # Create the artifact that the pipeline declares
    artifact = tmp_path / "artifacts" / "out.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}", encoding="utf-8")
    p = _make_pipeline(outputs=["artifacts/out.json"])
    # Override path to point to tmp_path
    p = p.model_copy(update={"path": tmp_path / "governance" / "pipelines" / "001--setup.md"})
    result = audit_drift(tmp_path, [p])
    codes = [f.code for f in result.findings]
    assert "AUDIT_MISSING_OUTPUT" not in codes
    assert "AUDIT_NO_DRIFT" in codes


def test_audit_drift_missing_output(tmp_path):
    p = _make_pipeline(outputs=["artifacts/missing.json"])
    result = audit_drift(tmp_path, [p])
    codes = [f.code for f in result.findings]
    assert "AUDIT_MISSING_OUTPUT" in codes


def test_audit_drift_skips_abstract_outputs(tmp_path):
    p = _make_pipeline(outputs=["none", "https://example.com/artifact", "N/A"])
    result = audit_drift(tmp_path, [p])
    codes = [f.code for f in result.findings]
    assert "AUDIT_MISSING_OUTPUT" not in codes


def test_audit_drift_mode(tmp_path):
    p = _make_pipeline()
    result = audit_drift(tmp_path, [p])
    assert result.mode == "drift"
