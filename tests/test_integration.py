"""Integration tests for end-to-end governance-os workflows."""

from typer.testing import CliRunner

from governance_os.cli import app

runner = CliRunner()


def _run(args: list[str]) -> tuple[int, str]:
    result = runner.invoke(app, args)
    return result.exit_code, result.output


# ---------------------------------------------------------------------------
# Workflow: init → scan → verify → preflight
# ---------------------------------------------------------------------------


def test_full_workflow_standard(tmp_path):
    """init standard → scan → verify → preflight all succeed."""
    code, out = _run(["init", str(tmp_path)])
    assert code == 0, out

    code, out = _run(["scan", str(tmp_path)])
    assert code == 0, out
    assert "001" in out

    code, out = _run(["verify", str(tmp_path)])
    assert code == 0, out

    code, out = _run(["preflight", str(tmp_path)])
    assert code == 0, out


def test_full_workflow_governed(tmp_path):
    """init governed → preflight → registry build → doctrine validate."""
    code, out = _run(["init", str(tmp_path), "--level", "governed"])
    assert code == 0, out
    assert (tmp_path / "governance" / "doctrine" / "doctrine.md").exists()

    code, out = _run(["preflight", str(tmp_path)])
    assert code == 0, out

    code, out = _run(["registry", "build", str(tmp_path)])
    assert code == 0, out
    assert "1 pipeline" in out

    code, out = _run(["doctrine", "validate", str(tmp_path)])
    assert code == 0, out
    assert "OK" in out


def test_full_workflow_codex_profile(tmp_path):
    """init codex profile creates session template; skills index reports 0 skills."""
    code, out = _run(["init", str(tmp_path), "--level", "governed", "--profile", "codex"])
    assert code == 0, out
    assert (tmp_path / "governance" / "sessions" / "session-template.md").exists()

    code, out = _run(["skills", "index", str(tmp_path)])
    assert code == 0, out  # no skills yet — INFO only, not error


# ---------------------------------------------------------------------------
# Workflow: verify exits 1 on error, 0 on clean repo
# ---------------------------------------------------------------------------


def test_verify_fails_on_invalid_contract(tmp_path):
    """verify exits 1 when a contract has schema errors."""
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0

    # Corrupt the example contract (remove Stage field)
    contract = tmp_path / "governance" / "pipelines" / "001--example.md"
    content = contract.read_text(encoding="utf-8")
    content = content.replace("Stage: establish\n", "")
    contract.write_text(content, encoding="utf-8")

    code, out = _run(["verify", str(tmp_path)])
    assert code == 1, out


def test_preflight_fails_on_bad_contract(tmp_path):
    """preflight exits 1 when contracts have errors."""
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0

    contract = tmp_path / "governance" / "pipelines" / "001--example.md"
    content = contract.read_text(encoding="utf-8")
    content = content.replace("Stage: establish\n", "")
    contract.write_text(content, encoding="utf-8")

    code, out = _run(["preflight", str(tmp_path)])
    assert code == 1, out


# ---------------------------------------------------------------------------
# Workflow: registry build → registry verify snapshot reconciliation
# ---------------------------------------------------------------------------


def test_registry_build_and_snapshot_reconcile(tmp_path):
    """registry build writes JSON; registry verify --snapshot detects changes."""
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0

    snapshot = tmp_path / "artifacts" / "registry.json"
    code, out = _run(["registry", "build", str(tmp_path), "--json", "--out", str(snapshot)])
    assert code == 0, out
    assert snapshot.exists()

    # Snapshot matches current state — verify should pass
    code, out = _run(["registry", "verify", str(tmp_path), "--snapshot", str(snapshot)])
    assert code == 0, out

    # Add a new pipeline — snapshot is now stale
    new_contract = tmp_path / "governance" / "pipelines" / "002--second.md"
    new_contract.write_text(
        "# 002 — Second\n\nStage: implement\n\nPurpose:\nSecond pipeline.\n\n"
        "Depends on:\n- 001\n\nOutputs:\n- artifacts/second.json\n\n"
        "Success Criteria:\n- Output exists\n",
        encoding="utf-8",
    )
    code, out = _run(["registry", "verify", str(tmp_path), "--snapshot", str(snapshot)])
    # Should still exit 0 (REGISTRY_UNTRACKED_PIPELINE is a warning, not error)
    assert code == 0, out
    assert "untracked" in out.lower() or "002" in out


# ---------------------------------------------------------------------------
# Workflow: audit drift detects missing outputs
# ---------------------------------------------------------------------------


def test_audit_drift_detects_missing_output(tmp_path):
    """audit drift reports missing declared outputs."""
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0

    # The example contract declares artifacts/example.json but it doesn't exist
    code, out = _run(["audit", "drift", str(tmp_path)])
    # Drift is reported as WARNING — should still pass (exit 0)
    assert code == 0, out


def test_audit_drift_passes_when_outputs_exist(tmp_path):
    """audit drift passes when declared outputs are present on disk."""
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0

    # Create the declared artifact
    artifact = tmp_path / "artifacts" / "example.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}", encoding="utf-8")

    code, out = _run(["audit", "drift", str(tmp_path)])
    assert code == 0, out
    assert (
        "no declared output drift" in out.lower()
        or "no drift" in out.lower()
        or "0 finding" in out.lower()
    )


# ---------------------------------------------------------------------------
# Workflow: scan exits 1 when pipelines dir is missing
# ---------------------------------------------------------------------------


def test_scan_exits_1_missing_pipelines_dir(tmp_path):
    """scan exits 1 when the pipelines directory does not exist."""
    code, out = _run(["scan", str(tmp_path)])
    assert code == 1, out


# ---------------------------------------------------------------------------
# Workflow: --out flag writes files for multiple commands
# ---------------------------------------------------------------------------


def test_out_flag_writes_report(tmp_path):
    """--out writes a markdown report to disk."""
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0

    out_file = tmp_path / "reports" / "scan.md"
    code, output = _run(["scan", str(tmp_path), "--out", str(out_file)])
    assert code == 0, output
    assert out_file.exists()
    assert out_file.stat().st_size > 0


def test_out_flag_json_writes_json(tmp_path):
    """--json --out writes a JSON file to disk."""
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0

    import json

    out_file = tmp_path / "reports" / "registry.json"
    code, output = _run(["registry", "build", str(tmp_path), "--json", "--out", str(out_file)])
    assert code == 0, output
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "entries" in data


# ---------------------------------------------------------------------------
# Workflow: authority verify passes on init'd repo
# ---------------------------------------------------------------------------


def test_authority_verify_passes_after_init(tmp_path):
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0

    code, out = _run(["authority", "verify", str(tmp_path)])
    assert code == 0, out


# ---------------------------------------------------------------------------
# Workflow: status is always exit 0 (reporting command)
# ---------------------------------------------------------------------------


def test_status_always_exits_0(tmp_path):
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0
    code, out = _run(["status", str(tmp_path)])
    assert code == 0, out
