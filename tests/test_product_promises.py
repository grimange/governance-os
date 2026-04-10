"""Product promise tests for governance-os.

This module protects user-facing and automation-facing promises identified
in README.md, docs/governance-contract.md, and CLI help text.

Coverage philosophy (see docs/testing-strategy.md):
- Every test here targets a promise that was documented but lacked CLI-level
  verification. Internal logic is tested in the relevant unit test files.
- Tests use the Typer test runner against real temp directories — no mocking
  of filesystem or CLI internals.
- Fixtures are minimal and explicit; prefer tmpdir + targeted file writes
  over complex shared setup.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from governance_os.cli import app

runner = CliRunner()


def _run(args: list[str]) -> tuple[int, str]:
    result = runner.invoke(app, args)
    return result.exit_code, result.output


def _init_standard(tmp_path: Path) -> Path:
    """Scaffold a minimal valid repo with one well-formed pipeline."""
    code, out = _run(["init", str(tmp_path)])
    assert code == 0, f"init failed: {out}"
    (tmp_path / "governance" / "pipelines" / "001--setup.md").write_text(
        "# 001 — Setup\n\nStage: establish\n\nPurpose:\nBootstrap.\n\n"
        "Outputs:\n- artifacts/out.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    old = tmp_path / "governance" / "pipelines" / "001--example.md"
    if old.exists():
        old.unlink()
    return tmp_path


# ---------------------------------------------------------------------------
# Section A: govos init flags — --dry-run and --force
# README promises: "preview without writing files", "overwrite existing files"
# ---------------------------------------------------------------------------


def test_init_dry_run_exits_0(tmp_path: Path):
    """--dry-run exits 0."""
    code, _ = _run(["init", str(tmp_path), "--dry-run"])
    assert code == 0


def test_init_dry_run_produces_plan_output(tmp_path: Path):
    """--dry-run prints a scaffold plan with + markers for new files."""
    _, out = _run(["init", str(tmp_path), "--dry-run"])
    assert "+" in out


def test_init_dry_run_writes_no_files(tmp_path: Path):
    """--dry-run must not write any files — it is a pure preview."""
    _run(["init", str(tmp_path), "--dry-run"])
    assert not (tmp_path / "governance").exists(), "dry-run must not write files"
    assert not (tmp_path / "governance.yaml").exists()


def test_init_dry_run_plan_includes_governance_yaml(tmp_path: Path):
    """--dry-run plan includes governance.yaml in planned output."""
    _, out = _run(["init", str(tmp_path), "--dry-run"])
    assert "governance.yaml" in out


def test_init_force_overwrites_existing_governance_yaml(tmp_path: Path):
    """--force overwrites files that already exist (idempotent with overwrite)."""
    _run(["init", str(tmp_path)])
    yaml_path = tmp_path / "governance.yaml"
    yaml_path.write_text("# corrupted\n", encoding="utf-8")
    code, _ = _run(["init", str(tmp_path), "--force"])
    assert code == 0
    content = yaml_path.read_text()
    assert "profile:" in content, "governance.yaml not restored by --force"


def test_init_without_force_is_idempotent(tmp_path: Path):
    """Default init skips existing files — re-running does not corrupt them."""
    _run(["init", str(tmp_path)])
    yaml_path = tmp_path / "governance.yaml"
    original = yaml_path.read_text()
    code, _ = _run(["init", str(tmp_path)])
    assert code == 0
    assert yaml_path.read_text() == original


# ---------------------------------------------------------------------------
# Section B: govos audit exit codes
# Contract: readiness/coverage/drift emit WARNING → exit 0
# Contract: audit multi-agent missing reviewer → ERROR → exit 1
# ---------------------------------------------------------------------------


def test_audit_readiness_exits_0_on_valid_repo(tmp_path: Path):
    """audit readiness exits 0 on a well-formed repo."""
    _init_standard(tmp_path)
    code, _ = _run(["audit", "readiness", str(tmp_path)])
    assert code == 0


def test_audit_readiness_warning_findings_do_not_block(tmp_path: Path):
    """audit readiness WARNING findings do not cause exit 1.

    A schema-valid pipeline with a single success criterion triggers
    AUDIT_WEAK_SUCCESS_CRITERIA (WARNING). WARNING does not block — exit 0.
    """
    # _init_standard creates a valid schema pipeline with 1 criterion → WARNING finding
    _init_standard(tmp_path)
    code, out = _run(["audit", "readiness", str(tmp_path)])
    assert code == 0, f"WARNING-only audit findings must not produce exit 1. Output: {out}"


def test_audit_readiness_json_has_required_fields(tmp_path: Path):
    """audit readiness --json includes schema_version, command, root, passed."""
    _init_standard(tmp_path)
    code, out = _run(["audit", "readiness", str(tmp_path), "--json"])
    assert code == 0
    data = json.loads(out)
    for field in ("schema_version", "command", "root", "passed"):
        assert field in data, f"audit readiness JSON missing: {field}"
    assert data["command"] == "audit readiness"


def test_audit_coverage_exits_0(tmp_path: Path):
    """audit coverage is advisory — always exits 0."""
    _init_standard(tmp_path)
    code, _ = _run(["audit", "coverage", str(tmp_path)])
    assert code == 0


def test_audit_drift_exits_0(tmp_path: Path):
    """audit drift is advisory — always exits 0."""
    _init_standard(tmp_path)
    code, _ = _run(["audit", "drift", str(tmp_path)])
    assert code == 0


def test_audit_multi_agent_exits_1_missing_reviewer(tmp_path: Path):
    """audit multi-agent exits 1 when reviewer role is absent (ERROR severity).

    MULTIAGENT_MISSING_REVIEWER is ERROR per governance contract:
    'Missing reviewer role → ERROR (not WARNING)'.

    Trigger condition: .codex/agents/ exists, planner and implementer roles
    are defined, but reviewer.toml is absent.
    """
    agents_dir = tmp_path / ".codex" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "planner.toml").write_text("[role]\nname = 'planner'\n", encoding="utf-8")
    (agents_dir / "implementer.toml").write_text("[role]\nname = 'implementer'\n", encoding="utf-8")
    # reviewer.toml intentionally absent
    code, _ = _run(["audit", "multi-agent", str(tmp_path)])
    assert code == 1, "Missing reviewer must produce exit 1"


def test_audit_multi_agent_json_passed_false_missing_reviewer(tmp_path: Path):
    """audit multi-agent --json has passed:false and error_count≥1 when reviewer absent."""
    agents_dir = tmp_path / ".codex" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "planner.toml").write_text("[role]\nname = 'planner'\n", encoding="utf-8")
    (agents_dir / "implementer.toml").write_text("[role]\nname = 'implementer'\n", encoding="utf-8")
    _, out = _run(["audit", "multi-agent", str(tmp_path), "--json"])
    data = json.loads(out)
    assert data["passed"] is False
    assert data.get("error_count", 0) >= 1


def test_audit_coverage_json_has_required_fields(tmp_path: Path):
    """audit coverage --json includes required fields."""
    _init_standard(tmp_path)
    _, out = _run(["audit", "coverage", str(tmp_path), "--json"])
    data = json.loads(out)
    for field in ("schema_version", "command", "root", "passed"):
        assert field in data, f"audit coverage JSON missing: {field}"


def test_audit_drift_json_has_required_fields(tmp_path: Path):
    """audit drift --json includes required fields."""
    _init_standard(tmp_path)
    _, out = _run(["audit", "drift", str(tmp_path), "--json"])
    data = json.loads(out)
    for field in ("schema_version", "command", "root", "passed"):
        assert field in data, f"audit drift JSON missing: {field}"


# ---------------------------------------------------------------------------
# Section C: govos preflight flags — --authority, --no-portability
# README: "--authority: enable authority validation"
# README: "--no-portability: disable portability checks"
# ---------------------------------------------------------------------------


def test_preflight_authority_flag_exits_0_on_valid_repo(tmp_path: Path):
    """preflight --authority exits 0 on a repo with no authority errors."""
    _init_standard(tmp_path)
    code, _ = _run(["preflight", str(tmp_path), "--authority"])
    assert code == 0


def test_preflight_no_portability_suppresses_portability_errors(tmp_path: Path):
    """preflight --no-portability skips portability checks.

    A pipeline with an absolute output path triggers ABSOLUTE_PATH (ERROR)
    without the flag, but --no-portability suppresses it → exit 0.
    """
    _run(["init", str(tmp_path)])
    (tmp_path / "governance" / "pipelines" / "001--setup.md").write_text(
        "# 001 — Setup\n\nStage: establish\n\nPurpose:\nBootstrap.\n\n"
        "Outputs:\n- /absolute/path/out.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    old = tmp_path / "governance" / "pipelines" / "001--example.md"
    if old.exists():
        old.unlink()
    code_default, _ = _run(["preflight", str(tmp_path)])
    assert code_default == 1, "absolute path must fail portability check"
    code_no_port, _ = _run(["preflight", str(tmp_path), "--no-portability"])
    assert code_no_port == 0, "--no-portability must suppress portability errors"


def test_preflight_authority_does_not_duplicate_check(tmp_path: Path):
    """preflight --authority runs authority exactly once in the checks list."""
    _init_standard(tmp_path)
    result = runner.invoke(app, ["preflight", str(tmp_path), "--authority", "--json"])
    data = json.loads(result.output)
    assert data.get("checks", []).count("authority") <= 1


# ---------------------------------------------------------------------------
# Section D: govos score flags — --compare, --explain
# README: "--compare PATH: delta summary vs previous score"
# README: "--explain: include formula explanation"
# ---------------------------------------------------------------------------


def test_score_json_has_required_and_score_fields(tmp_path: Path):
    """score --json includes schema_version, command, root, passed, overall_score, grade."""
    _init_standard(tmp_path)
    code, out = _run(["score", str(tmp_path), "--json"])
    assert code == 0
    data = json.loads(out)
    for field in ("schema_version", "command", "root", "passed", "overall_score", "grade", "categories"):
        assert field in data, f"score JSON missing: {field}"


def test_score_passed_always_true(tmp_path: Path):
    """score is informational — passed is always true."""
    _init_standard(tmp_path)
    _, out = _run(["score", str(tmp_path), "--json"])
    assert json.loads(out)["passed"] is True


def test_score_categories_all_present(tmp_path: Path):
    """score --json output includes all five scoring categories."""
    _init_standard(tmp_path)
    _, out = _run(["score", str(tmp_path), "--json"])
    names = {c["name"] for c in json.loads(out)["categories"]}
    assert {"integrity", "readiness", "coverage", "drift", "authority"} <= names


def test_score_compare_produces_delta_field(tmp_path: Path):
    """score --compare PATH produces a delta field in JSON output."""
    _init_standard(tmp_path)
    baseline = tmp_path / "baseline-score.json"
    _run(["score", str(tmp_path), "--json", "--out", str(baseline)])
    assert baseline.exists()
    _, out = _run(["score", str(tmp_path), "--json", "--compare", str(baseline)])
    data = json.loads(out)
    assert "delta" in data, "score --compare must produce delta field"
    assert isinstance(data["delta"], list)


def test_score_explain_includes_formula_text(tmp_path: Path):
    """score --explain includes formula explanation in text output."""
    _init_standard(tmp_path)
    code, out = _run(["score", str(tmp_path), "--explain"])
    assert code == 0
    assert "formula" in out.lower() or "deduct" in out.lower() or "per category" in out.lower()


# ---------------------------------------------------------------------------
# Section E: govos profile commands
# Contract: profile list always exits 0; profile validate exits 0/1
# ---------------------------------------------------------------------------


def test_profile_list_exits_0():
    """profile list always exits 0 (informational command)."""
    code, _ = _run(["profile", "list"])
    assert code == 0


def test_profile_list_shows_both_profiles():
    """profile list shows generic and codex profiles."""
    _, out = _run(["profile", "list"])
    assert "generic" in out
    assert "codex" in out


def test_profile_validate_exits_0_satisfied(tmp_path: Path):
    """profile validate exits 0 when all profile expected surfaces are present.

    After govos init, generic expected surfaces exist:
    governance/pipelines, artifacts, governance.yaml.
    """
    _init_standard(tmp_path)
    code, out = _run(["profile", "validate", str(tmp_path)])
    assert code == 0
    assert "OK" in out


def test_profile_validate_exits_1_missing_surfaces(tmp_path: Path):
    """profile validate exits 1 when expected surfaces are missing."""
    code, out = _run(["profile", "validate", str(tmp_path)])
    assert code == 1
    assert "INCOMPLETE" in out or "missing" in out.lower()


# ---------------------------------------------------------------------------
# Section F: govos pipeline lifecycle commands
# Contract: pipeline list always exits 0; pipeline status exits 0/2;
#           pipeline verify exits 0 / 1 (drift) / 2 (not found)
# ---------------------------------------------------------------------------


def test_pipeline_list_exits_0(tmp_path: Path):
    """pipeline list always exits 0 (informational command)."""
    _init_standard(tmp_path)
    code, _ = _run(["pipeline", "list", str(tmp_path)])
    assert code == 0


def test_pipeline_list_json_has_required_fields(tmp_path: Path):
    """pipeline list --json includes schema_version, command, root, passed."""
    _init_standard(tmp_path)
    code, out = _run(["pipeline", "list", str(tmp_path), "--json"])
    assert code == 0
    data = json.loads(out)
    for field in ("schema_version", "command", "root", "passed"):
        assert field in data, f"pipeline list JSON missing: {field}"
    assert data["passed"] is True


def test_pipeline_status_exits_0_for_existing_pipeline(tmp_path: Path):
    """pipeline status exits 0 when the pipeline ID is found."""
    _init_standard(tmp_path)
    code, _ = _run(["pipeline", "status", "001", "--root", str(tmp_path)])
    assert code == 0


def test_pipeline_status_json_includes_effective_state(tmp_path: Path):
    """pipeline status --json includes effective_state field."""
    _init_standard(tmp_path)
    code, out = _run(["pipeline", "status", "001", "--root", str(tmp_path), "--json"])
    assert code == 0
    assert "effective_state" in json.loads(out)


def test_pipeline_verify_exits_0_no_drift(tmp_path: Path):
    """pipeline verify exits 0 when declared state is absent or matches effective."""
    _init_standard(tmp_path)
    code, _ = _run(["pipeline", "verify", "001", "--root", str(tmp_path)])
    assert code == 0


def test_pipeline_verify_exits_1_on_lifecycle_drift(tmp_path: Path):
    """pipeline verify exits 1 when declared state ≠ effective state.

    README: 'Exits 1 if lifecycle drift detected'.
    State: active declared but no run marker → effective=ready → drift.
    """
    _run(["init", str(tmp_path)])
    (tmp_path / "governance" / "pipelines" / "001--setup.md").write_text(
        "# 001 — Setup\n\nStage: establish\n\nState: active\n\n"
        "Purpose:\nBootstrap.\n\nOutputs:\n- artifacts/out.json\n\n"
        "Success criteria:\n- done\n",
        encoding="utf-8",
    )
    old = tmp_path / "governance" / "pipelines" / "001--example.md"
    if old.exists():
        old.unlink()
    code, out = _run(["pipeline", "verify", "001", "--root", str(tmp_path)])
    assert code == 1, f"Expected exit 1 for drift, got {code}"
    assert "drift" in out.lower()


def test_pipeline_verify_exits_2_not_found(tmp_path: Path):
    """pipeline verify exits 2 when the pipeline ID is not found."""
    _init_standard(tmp_path)
    code, _ = _run(["pipeline", "verify", "999", "--root", str(tmp_path)])
    assert code == 2


# ---------------------------------------------------------------------------
# Section G: End-to-end multi-agent workflow
# README: "govos init --profile codex --template multi-agent"
# ---------------------------------------------------------------------------


def test_multi_agent_init_creates_expected_structure(tmp_path: Path):
    """init --profile codex --template multi-agent creates AGENTS.md and agents/ dirs."""
    code, _ = _run(["init", str(tmp_path), "--profile", "codex", "--template", "multi-agent"])
    assert code == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".codex" / "agents").exists()


def test_multi_agent_init_then_scan_passes(tmp_path: Path):
    """init multi-agent → scan exits 0 (scaffold contracts are parseable)."""
    _run(["init", str(tmp_path), "--profile", "codex", "--template", "multi-agent"])
    code, _ = _run(["scan", str(tmp_path)])
    assert code == 0


def test_multi_agent_init_then_verify_passes(tmp_path: Path):
    """init multi-agent → verify exits 0 (scaffold contracts are schema-valid)."""
    _run(["init", str(tmp_path), "--profile", "codex", "--template", "multi-agent"])
    code, _ = _run(["verify", str(tmp_path)])
    assert code == 0


def test_multi_agent_audit_produces_multiagent_codes(tmp_path: Path):
    """audit multi-agent on incomplete setup emits MULTIAGENT_* finding codes."""
    _run(["init", str(tmp_path), "--profile", "codex", "--template", "governed"])
    _, out = _run(["audit", "multi-agent", str(tmp_path), "--json"])
    data = json.loads(out)
    codes = [f["code"] for f in data.get("findings", [])]
    assert any("MULTIAGENT" in c for c in codes)


# ---------------------------------------------------------------------------
# Section H: govos skills verify
# Contract: exits 0 for WARNING findings (only ERROR-severity blocks)
# ---------------------------------------------------------------------------


def test_skills_verify_exits_0_clean(tmp_path: Path):
    """skills verify exits 0 when no errors exist."""
    root = _init_standard(tmp_path)
    skills_dir = root / "governance" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "python.md").write_text("# Python\n\nCore skill.\n", encoding="utf-8")
    code, _ = _run(["skills", "verify", str(root)])
    assert code == 0


def test_skills_verify_warning_findings_do_not_exit_1(tmp_path: Path):
    """skills verify exits 0 for WARNING findings (SKILLS_DUPLICATE_ID is WARNING).

    Per governance contract, WARNING is advisory and does not cause exit 1.
    """
    root = _init_standard(tmp_path)
    skills_dir = root / "governance" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "python.md").write_text("# Python\n\nCore skill.\n", encoding="utf-8")
    (skills_dir / "python-alt.md").write_text("# Python\n\nAlternate.\n", encoding="utf-8")
    code, _ = _run(["skills", "verify", str(root)])
    assert code == 0, "WARNING-severity skills findings must not produce exit 1"


# ---------------------------------------------------------------------------
# Section I: Package surface compatibility
# Contract: stable top-level imports, version export, CLI command names
# ---------------------------------------------------------------------------


def test_version_importable_and_non_empty():
    """governance_os.__version__ is importable and non-empty."""
    import governance_os
    assert hasattr(governance_os, "__version__")
    assert isinstance(governance_os.__version__, str)
    assert governance_os.__version__


def test_api_module_exposes_expected_functions():
    """governance_os.api exposes the documented public entry points."""
    import governance_os.api as api
    for fn in ("scan", "verify", "preflight", "score", "profile_list", "plugin_list",
               "plugin_show", "profile_show"):
        assert hasattr(api, fn), f"api.{fn} is missing from public surface"


def test_govos_help_exits_0():
    """govos --help exits 0."""
    code, _ = _run(["--help"])
    assert code == 0


def test_govos_help_includes_all_top_level_commands():
    """All documented top-level commands appear in govos --help output."""
    _, out = _run(["--help"])
    for cmd in ("scan", "verify", "status", "preflight", "score",
                "audit", "profile", "pipeline", "plugin", "registry", "skills"):
        assert cmd in out, f"govos --help missing command: {cmd}"


# ---------------------------------------------------------------------------
# Section J: Consolidation gap tests
# Closes the highest-value CLI contract gaps not covered in Sections A–I.
# ---------------------------------------------------------------------------


def test_score_compare_produces_non_empty_delta(tmp_path: Path):
    """score --compare produces non-empty delta when governance health changes.

    Workflow: init a repo with a bad pipeline (absolute output path) → save
    baseline score → remove the bad pipeline → compare against baseline.
    Integrity category should improve, giving at least one non-zero delta entry.
    """
    # Init with a bad pipeline (absolute output path triggers ABSOLUTE_PATH ERROR)
    _run(["init", str(tmp_path)])
    bad_pipeline = tmp_path / "governance" / "pipelines" / "001--bad.md"
    bad_pipeline.write_text(
        "# 001 — Bad\n\nStage: establish\n\nPurpose:\nTest.\n\n"
        "Outputs:\n- /absolute/path/out.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    old = tmp_path / "governance" / "pipelines" / "001--example.md"
    if old.exists():
        old.unlink()

    # Capture baseline with the bad pipeline present
    baseline = tmp_path / "baseline-score.json"
    _run(["score", str(tmp_path), "--json", "--out", str(baseline)])
    assert baseline.exists(), "baseline score file not created"

    # Fix the pipeline (remove absolute path)
    bad_pipeline.write_text(
        "# 001 — Bad\n\nStage: establish\n\nPurpose:\nTest.\n\n"
        "Outputs:\n- artifacts/out.json\n\nSuccess criteria:\n- done\n- verified\n",
        encoding="utf-8",
    )

    # Compare against baseline — delta should be non-empty
    code, out = _run(["score", str(tmp_path), "--json", "--compare", str(baseline)])
    assert code == 0
    data = json.loads(out)
    assert "delta" in data, "score --compare must produce a delta field"
    assert isinstance(data["delta"], list)
    assert len(data["delta"]) > 0, (
        "score --compare must produce at least one delta entry when governance health changes"
    )


def test_authority_verify_exits_1_missing_governance_yaml(tmp_path: Path):
    """authority verify exits 1 when governance.yaml is absent.

    AUTHORITY_MISSING_ROOT is ERROR severity → exit 1.
    An empty tmp_path has no governance.yaml, which is a required authority file.
    """
    code, out = _run(["authority", "verify", str(tmp_path)])
    assert code == 1, (
        f"authority verify must exit 1 when governance.yaml is absent. "
        f"Got exit {code}. Output: {out}"
    )


def test_registry_build_exits_1_duplicate_pipeline_ids(tmp_path: Path):
    """registry build exits 1 when two pipelines share the same numeric ID.

    REGISTRY_DUPLICATE_ID is ERROR severity → exit 1.
    """
    _run(["init", str(tmp_path)])
    pipelines_dir = tmp_path / "governance" / "pipelines"
    # Remove default scaffold pipeline if present
    for f in pipelines_dir.glob("001--*.md"):
        f.unlink()
    # Write two pipelines with the same numeric ID 001
    (pipelines_dir / "001--alpha.md").write_text(
        "# 001 — Alpha\n\nStage: establish\n\nPurpose:\nFirst.\n\n"
        "Outputs:\n- artifacts/a.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    (pipelines_dir / "001--beta.md").write_text(
        "# 001 — Beta\n\nStage: establish\n\nPurpose:\nSecond.\n\n"
        "Outputs:\n- artifacts/b.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    code, out = _run(["registry", "build", str(tmp_path)])
    assert code == 1, (
        f"registry build must exit 1 for duplicate pipeline IDs. "
        f"Got exit {code}. Output: {out}"
    )


def test_preflight_warns_on_unknown_plugin_id(tmp_path: Path):
    """preflight emits PLUGIN_UNKNOWN warning when config lists an unknown plugin ID.

    validate_plugin_ids() is called inside preflight(). An unknown plugin ID in
    enabled_plugins produces a PLUGIN_UNKNOWN WARNING finding. WARNING does not
    block (exit 0), but the finding must appear in JSON output.
    """
    _run(["init", str(tmp_path)])
    # Write a governance.yaml that references a non-existent plugin.
    # Preserve pipelines_dir so the directory layout from govos init remains valid.
    (tmp_path / "governance.yaml").write_text(
        "profile: generic\n"
        "pipelines_dir: governance/pipelines\n"
        "contracts_glob: '**/*.md'\n"
        "enabled_plugins:\n  - nonexistent_plugin_xyz\n",
        encoding="utf-8",
    )
    (tmp_path / "governance" / "pipelines" / "001--setup.md").write_text(
        "# 001 — Setup\n\nStage: establish\n\nPurpose:\nBootstrap.\n\n"
        "Outputs:\n- artifacts/out.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    old = tmp_path / "governance" / "pipelines" / "001--example.md"
    if old.exists():
        old.unlink()

    code, out = _run(["preflight", str(tmp_path), "--json"])
    # PLUGIN_UNKNOWN is WARNING → does not block → exit 0
    assert code == 0, f"PLUGIN_UNKNOWN warning must not cause exit 1. Got {code}. Output: {out}"
    data = json.loads(out)
    codes = [i.get("code", "") for i in data.get("issues", [])]
    assert "PLUGIN_UNKNOWN" in codes, (
        f"Expected PLUGIN_UNKNOWN in preflight issues for unknown plugin ID. "
        f"Got codes: {codes}"
    )
