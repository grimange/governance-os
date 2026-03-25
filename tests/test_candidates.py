"""Tests for contract-candidate discovery."""

from pathlib import Path

from governance_os.discovery.candidates import CandidateResult, discover_candidates
from governance_os.models.pipeline import Pipeline


def _make_pipeline(num_id: str, slug: str) -> Pipeline:
    return Pipeline(
        numeric_id=num_id,
        slug=slug,
        path=Path(f"governance/pipelines/{num_id}--{slug}.md"),
        title=f"Pipeline {num_id}",
        stage="establish",
        purpose="Test.",
        outputs=["artifacts/out.json"],
        success_criteria=["Done"],
    )


def test_discover_candidates_empty_repo(tmp_path):
    result = discover_candidates(tmp_path, [])
    assert isinstance(result, CandidateResult)
    assert result.candidate_count == 0


def test_discover_candidates_high_confidence_makefile(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "Makefile").touch()
    result = discover_candidates(tmp_path, [])
    high = result.by_confidence("high")
    assert len(high) >= 1
    assert any(c.path == scripts_dir for c in high)


def test_discover_candidates_medium_confidence(tmp_path):
    ci_dir = tmp_path / "ci"
    ci_dir.mkdir()
    (ci_dir / "pipeline.yaml").touch()
    result = discover_candidates(tmp_path, [])
    medium = result.by_confidence("medium")
    assert len(medium) >= 1


def test_discover_candidates_excludes_contracted(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "Makefile").touch()
    p = _make_pipeline("001", "scripts")
    result = discover_candidates(tmp_path, [p])
    # scripts is already contracted, should not appear
    script_candidates = [c for c in result.candidates if c.path == scripts_dir]
    assert not script_candidates


def test_discover_candidates_suggested_id_format(tmp_path):
    scripts_dir = tmp_path / "deploy"
    scripts_dir.mkdir()
    (scripts_dir / "deploy.sh").touch()
    result = discover_candidates(tmp_path, [])
    assert result.candidate_count >= 1
    for c in result.candidates:
        if c.suggested_id is not None:
            assert c.suggested_id.isdigit() or len(c.suggested_id) == 3


def test_discover_candidates_ignores_hidden_dirs(tmp_path):
    hidden_dir = tmp_path / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "Makefile").touch()
    result = discover_candidates(tmp_path, [])
    hidden_candidates = [c for c in result.candidates if c.path == hidden_dir]
    assert not hidden_candidates


def test_discover_candidates_json_via_cli(tmp_path):
    import json

    from typer.testing import CliRunner

    from governance_os.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["discover", "candidates", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["command"] == "discover candidates"
    assert "candidates" in data
