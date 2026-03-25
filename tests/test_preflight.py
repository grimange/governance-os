"""Tests for the preflight command and API."""

import json
from pathlib import Path

from typer.testing import CliRunner

from governance_os.cli import app

runner = CliRunner()


def _init_repo(tmp_path: Path) -> Path:
    runner.invoke(app, ["init", str(tmp_path)])
    pipeline = tmp_path / "governance" / "pipelines" / "001--setup.md"
    pipeline.write_text(
        "# 001 — Setup\n\nStage: establish\n\nPurpose:\nBootstrap.\n\n"
        "Outputs:\n- artifacts/out.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    old = tmp_path / "governance" / "pipelines" / "001--example.md"
    if old.exists():
        old.unlink()
    return tmp_path


def test_preflight_passes_for_valid_repo(tmp_path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["preflight", str(root)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_preflight_fails_for_invalid_contract(tmp_path):
    root = _init_repo(tmp_path)
    bad = root / "governance" / "pipelines" / "002--broken.md"
    bad.write_text("# 002 — Broken\n\n(no required sections)\n", encoding="utf-8")
    result = runner.invoke(app, ["preflight", str(root)])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_preflight_json_output(tmp_path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["preflight", str(root), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["command"] == "preflight"
    assert "passed" in data
    assert "checks" in data
    assert "error_count" in data


def test_preflight_with_portability_issues(tmp_path):
    root = _init_repo(tmp_path)
    bad = root / "governance" / "pipelines" / "002--bad.md"
    bad.write_text(
        "# 002 — Bad\n\nStage: implement\n\nPurpose:\nBad.\n\n"
        "Outputs:\n- /absolute/path\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["preflight", str(root)])
    assert result.exit_code == 1


def test_preflight_api(tmp_path):
    import governance_os.api as api

    root = _init_repo(tmp_path)
    result = api.preflight(root)
    assert result.passed
    assert "contract-parsing" in result.checks
    assert "schema-validation" in result.checks
    assert "portability" in result.checks
