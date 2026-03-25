"""Tests for the authority validation module."""

from pathlib import Path

from governance_os.authority.core import verify_authority
from governance_os.models.pipeline import Pipeline


def _make_pipeline(
    num_id: str = "001",
    slug: str = "setup",
    depends_on: list | None = None,
    path: Path | None = None,
) -> Pipeline:
    return Pipeline(
        numeric_id=num_id,
        slug=slug,
        path=path or Path(f"governance/pipelines/{num_id}--{slug}.md"),
        title=f"Pipeline {num_id}",
        stage="establish",
        purpose="Test.",
        outputs=["artifacts/out.json"],
        success_criteria=["Done"],
        depends_on=depends_on or [],
    )


def test_authority_passes_with_config(tmp_path):
    (tmp_path / "governance.yaml").write_text(
        "pipelines_dir: governance/pipelines\n", encoding="utf-8"
    )
    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    p = _make_pipeline(path=tmp_path / "governance" / "pipelines" / "001--setup.md")
    result = verify_authority(tmp_path, [p])
    error_codes = [i.code for i in result.issues if i.severity.value == "error"]
    assert not error_codes
    assert result.passed


def test_authority_missing_config(tmp_path):
    p = _make_pipeline()
    result = verify_authority(tmp_path, [p])
    codes = [i.code for i in result.issues]
    assert "AUTHORITY_MISSING_ROOT" in codes
    assert not result.passed


def test_authority_contract_in_artifact_dir(tmp_path):
    (tmp_path / "governance.yaml").write_text(
        "pipelines_dir: governance/pipelines\n", encoding="utf-8"
    )
    artifact_dir = tmp_path / "artifacts" / "generated"
    artifact_dir.mkdir(parents=True)
    contract_path = artifact_dir / "001--setup.md"
    contract_path.touch()
    p = _make_pipeline(path=contract_path)
    result = verify_authority(tmp_path, [p])
    codes = [i.code for i in result.issues]
    assert "AUTHORITY_CONTRACT_IN_ARTIFACT_DIR" in codes


def test_authority_path_dependency(tmp_path):
    (tmp_path / "governance.yaml").write_text(
        "pipelines_dir: governance/pipelines\n", encoding="utf-8"
    )
    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    p = _make_pipeline(
        depends_on=["governance/pipelines/001--other.md"],
        path=tmp_path / "governance" / "pipelines" / "002--setup.md",
    )
    result = verify_authority(tmp_path, [p])
    codes = [i.code for i in result.issues]
    assert "AUTHORITY_PATH_DEPENDENCY" in codes


def test_authority_numeric_dependency_ok(tmp_path):
    (tmp_path / "governance.yaml").write_text(
        "pipelines_dir: governance/pipelines\n", encoding="utf-8"
    )
    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    p = _make_pipeline(
        depends_on=["001"],
        path=tmp_path / "governance" / "pipelines" / "002--setup.md",
    )
    result = verify_authority(tmp_path, [p])
    path_dep_codes = [i.code for i in result.issues if i.code == "AUTHORITY_PATH_DEPENDENCY"]
    assert not path_dep_codes


def test_authority_config_dir_missing(tmp_path):
    (tmp_path / "governance.yaml").write_text("pipelines_dir: nonexistent/dir\n", encoding="utf-8")
    p = _make_pipeline(path=tmp_path / "nonexistent" / "dir" / "001--setup.md")
    result = verify_authority(tmp_path, [p])
    codes = [i.code for i in result.issues]
    assert "AUTHORITY_CONFIG_DIR_MISSING" in codes
