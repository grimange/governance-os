"""CLI smoke tests for governance-os."""

from pathlib import Path

from typer.testing import CliRunner

from governance_os.cli import app

runner = CliRunner()


def _init_repo(tmp_path: Path) -> Path:
    """Initialise a repo and add one valid pipeline."""
    runner.invoke(app, ["init", str(tmp_path)])
    pipeline = tmp_path / "governance" / "pipelines" / "001--setup.md"
    pipeline.write_text(
        "# 001 — Setup\n\nStage: establish\n\nPurpose:\nBootstrap.\n\n"
        "Outputs:\n- artifacts/out.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    # Remove the scaffold example which uses the old naming convention
    old = tmp_path / "governance" / "pipelines" / "001--example.md"
    if old.exists():
        old.unlink()
    return tmp_path


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_init_help():
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0


def test_portability_scan_help():
    result = runner.invoke(app, ["portability", "scan", "--help"])
    assert result.exit_code == 0


def test_init_creates_structure(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "governance.yaml").exists()


def test_init_idempotent(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "skipped" in result.output.lower()


def test_scan_finds_pipeline(tmp_path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["scan", str(root)])
    assert result.exit_code == 0
    assert "001" in result.output


def test_scan_missing_dir(tmp_path):
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert (
        "0 pipeline" in result.output
        or "not found" in result.output.lower()
        or "parse error" in result.output.lower()
    )


def test_scan_json_valid(tmp_path):
    import json

    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["scan", str(root), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["command"] == "scan"
    assert "pipelines" in data


def test_verify_passes_for_valid_pipeline(tmp_path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["verify", str(root)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_verify_json_valid(tmp_path):
    import json

    root = _init_repo(tmp_path)
    # verify returns 0 for passing repo
    json_result = runner.invoke(app, ["verify", str(root), "--json"])
    data = json.loads(json_result.output)
    assert data["command"] == "verify"
    assert "passed" in data


def test_status_lists_pipelines(tmp_path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["status", str(root)])
    assert result.exit_code == 0
    assert "001" in result.output


def test_status_json_valid(tmp_path):
    import json

    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["status", str(root), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["command"] == "status"
    assert "records" in data


def test_portability_scan_passes_clean(tmp_path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["portability", "scan", str(root)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_portability_scan_json_valid(tmp_path):
    import json

    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["portability", "scan", str(root), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["command"] == "portability scan"
    assert "passed" in data


def test_verify_fails_for_bad_pipeline(tmp_path):
    root = _init_repo(tmp_path)
    bad = root / "governance" / "pipelines" / "002--broken.md"
    bad.write_text("# 002 — Broken\n\n(no required sections)\n", encoding="utf-8")
    result = runner.invoke(app, ["verify", str(root)])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_portability_scan_fails_for_absolute_path(tmp_path):
    root = _init_repo(tmp_path)
    bad = root / "governance" / "pipelines" / "002--bad-path.md"
    bad.write_text(
        "# 002 — Bad Path\n\nStage: implement\n\nPurpose:\nBad.\n\n"
        "Outputs:\n- /absolute/path\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["portability", "scan", str(root)])
    assert result.exit_code == 1
