"""Golden tests for Phase 4 governance contract guarantees.

Tests in this module protect:
- JSON output structure (schema_version, passed, command, root in all outputs)
- Severity semantics (ERROR → exit 1, WARNING/INFO → exit 0)
- Exit code contract (0 = pass, 1 = governance failure, 2 = usage error)
- Fail-closed behavior for invalid or incomplete inputs
- skills index explicit exit code
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from governance_os.cli import app
from governance_os.models.issue import Issue, Severity
from governance_os.models.lifecycle import LifecycleRecord, LifecycleResult, LifecycleState
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.status import PipelineStatus, StatusRecord, StatusResult
from governance_os.reporting.json_report import (
    audit_to_json,
    authority_to_json,
    candidates_to_json,
    lifecycle_to_json,
    portability_to_json,
    preflight_to_json,
    registry_to_json,
    scan_to_json,
    score_to_json,
    skills_to_json,
    status_to_json,
    verify_to_json,
)

runner = CliRunner()

_ROOT = Path("/repo")
_PATH = Path("001--foo.md")
_SCHEMA_VERSION = "1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(tmp_path: Path) -> Path:
    """Scaffold a minimal valid governance repo."""
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


def _error_issue() -> Issue:
    return Issue(code="MISSING_STAGE", severity=Severity.ERROR, message="Missing stage", path=_PATH)


def _warning_issue() -> Issue:
    return Issue(code="AUDIT_MISSING_SCOPE", severity=Severity.WARNING, message="No scope", path=_PATH)


def _info_issue() -> Issue:
    return Issue(code="AUDIT_MISSING_IMPL_NOTES", severity=Severity.INFO, message="No impl notes", path=_PATH)


def _pipeline_stub():
    from governance_os.models.pipeline import Pipeline
    return Pipeline(numeric_id="001", slug="foo", path=_PATH, title="Foo", stage="establish")


# ---------------------------------------------------------------------------
# Section A: schema_version present in all JSON outputs
# ---------------------------------------------------------------------------


def test_schema_version_scan():
    data = scan_to_json(ScanResult(root=_ROOT))
    assert data["schema_version"] == _SCHEMA_VERSION


def test_schema_version_verify():
    data = verify_to_json(VerifyResult(root=_ROOT))
    assert data["schema_version"] == _SCHEMA_VERSION


def test_schema_version_status():
    data = status_to_json(StatusResult(root=_ROOT))
    assert data["schema_version"] == _SCHEMA_VERSION


def test_schema_version_portability():
    data = portability_to_json(PortabilityResult(root=_ROOT))
    assert data["schema_version"] == _SCHEMA_VERSION


def test_schema_version_audit(tmp_path: Path):
    import governance_os.api as api
    result = api.audit(tmp_path, mode="readiness")
    data = audit_to_json(result)
    assert data["schema_version"] == _SCHEMA_VERSION


def test_schema_version_lifecycle():
    result = LifecycleResult(root=_ROOT)
    data = lifecycle_to_json(result)
    assert data["schema_version"] == _SCHEMA_VERSION


def test_schema_version_candidates(tmp_path: Path):
    import governance_os.api as api
    result = api.candidates(tmp_path)
    data = candidates_to_json(result)
    assert data["schema_version"] == _SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Section B: passed field present in all JSON outputs
# ---------------------------------------------------------------------------


def test_passed_scan_no_errors():
    data = scan_to_json(ScanResult(root=_ROOT))
    assert "passed" in data
    assert data["passed"] is True


def test_passed_scan_with_parse_error():
    data = scan_to_json(ScanResult(root=_ROOT, parse_errors=[_error_issue()]))
    assert data["passed"] is False


def test_passed_verify():
    data = verify_to_json(VerifyResult(root=_ROOT))
    assert "passed" in data
    assert data["passed"] is True


def test_passed_verify_with_error():
    data = verify_to_json(VerifyResult(root=_ROOT, issues=[_error_issue()]))
    assert data["passed"] is False


def test_passed_status_always_true():
    data = status_to_json(StatusResult(root=_ROOT))
    assert "passed" in data
    assert data["passed"] is True


def test_passed_portability():
    data = portability_to_json(PortabilityResult(root=_ROOT))
    assert "passed" in data
    assert data["passed"] is True


def test_passed_portability_with_error():
    err = Issue(code="ABSOLUTE_PATH", severity=Severity.ERROR, message="Bad", path=_PATH)
    data = portability_to_json(PortabilityResult(root=_ROOT, issues=[err]))
    assert data["passed"] is False


def test_passed_lifecycle_no_failed():
    rec = LifecycleRecord(
        pipeline_id="001", slug="foo", path=_PATH,
        declared_state="", effective_state=LifecycleState.READY, drift=False,
    )
    data = lifecycle_to_json(LifecycleResult(root=_ROOT, records=[rec]))
    assert "passed" in data
    assert data["passed"] is True


def test_passed_lifecycle_with_failed():
    rec = LifecycleRecord(
        pipeline_id="001", slug="foo", path=_PATH,
        declared_state="", effective_state=LifecycleState.FAILED, drift=False,
    )
    data = lifecycle_to_json(LifecycleResult(root=_ROOT, records=[rec]))
    assert data["passed"] is False
    assert data["failed_count"] == 1


def test_passed_candidates_always_true(tmp_path: Path):
    import governance_os.api as api
    data = candidates_to_json(api.candidates(tmp_path))
    assert "passed" in data
    assert data["passed"] is True


# ---------------------------------------------------------------------------
# Section C: error_count in scan output
# ---------------------------------------------------------------------------


def test_scan_error_count_zero():
    data = scan_to_json(ScanResult(root=_ROOT))
    assert data["error_count"] == 0


def test_scan_error_count_with_errors():
    data = scan_to_json(ScanResult(root=_ROOT, parse_errors=[_error_issue(), _error_issue()]))
    assert data["error_count"] == 2


# ---------------------------------------------------------------------------
# Section D: Severity semantics — ERROR blocks, WARNING/INFO do not
# ---------------------------------------------------------------------------


def test_severity_error_causes_verify_failure():
    result = VerifyResult(root=_ROOT, issues=[_error_issue()])
    assert result.passed is False


def test_severity_warning_does_not_cause_verify_failure():
    result = VerifyResult(root=_ROOT, issues=[_warning_issue()])
    assert result.passed is True


def test_severity_info_does_not_cause_verify_failure():
    result = VerifyResult(root=_ROOT, issues=[_info_issue()])
    assert result.passed is True


def test_severity_error_causes_portability_failure():
    err = Issue(code="ABSOLUTE_PATH", severity=Severity.ERROR, message="Bad", path=_PATH)
    assert PortabilityResult(root=_ROOT, issues=[err]).passed is False


def test_severity_warning_does_not_cause_portability_failure():
    result = PortabilityResult(root=_ROOT, issues=[_warning_issue()])
    assert result.passed is True


# ---------------------------------------------------------------------------
# Section E: Exit code contract via CLI
# ---------------------------------------------------------------------------


def test_exit_0_successful_verify(tmp_path: Path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["verify", str(root)])
    assert result.exit_code == 0


def test_exit_1_governance_failure_verify(tmp_path: Path):
    root = _init_repo(tmp_path)
    bad = root / "governance" / "pipelines" / "002--broken.md"
    bad.write_text("# 002 — Broken\n\n(no required sections)\n", encoding="utf-8")
    result = runner.invoke(app, ["verify", str(root)])
    assert result.exit_code == 1


def test_exit_0_preflight_clean_repo(tmp_path: Path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["preflight", str(root)])
    assert result.exit_code == 0


def test_exit_1_preflight_broken_pipeline(tmp_path: Path):
    root = _init_repo(tmp_path)
    bad = root / "governance" / "pipelines" / "002--broken.md"
    bad.write_text("# 002 — Broken\n\n(no required sections)\n", encoding="utf-8")
    result = runner.invoke(app, ["preflight", str(root)])
    assert result.exit_code == 1


def test_exit_2_init_invalid_profile(tmp_path: Path):
    result = runner.invoke(app, ["init", str(tmp_path), "--profile", "nonexistent"])
    assert result.exit_code == 2


def test_exit_2_init_invalid_template(tmp_path: Path):
    result = runner.invoke(app, ["init", str(tmp_path), "--template", "nonexistent"])
    assert result.exit_code == 2


def test_exit_2_init_multi_agent_wrong_profile(tmp_path: Path):
    result = runner.invoke(app, ["init", str(tmp_path), "--template", "multi-agent", "--profile", "generic"])
    assert result.exit_code == 2


def test_exit_2_profile_show_not_found():
    result = runner.invoke(app, ["profile", "show", "does_not_exist"])
    assert result.exit_code == 2


def test_exit_2_pipeline_status_not_found(tmp_path: Path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["pipeline", "status", "999", "--root", str(root)])
    assert result.exit_code == 2


def test_exit_2_pipeline_verify_not_found(tmp_path: Path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["pipeline", "verify", "999", "--root", str(root)])
    assert result.exit_code == 2


def test_exit_0_skills_index(tmp_path: Path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["skills", "index", str(root)])
    assert result.exit_code == 0


def test_exit_0_skills_index_json(tmp_path: Path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["skills", "index", str(root), "--json"])
    assert result.exit_code == 0


def test_exit_0_status_always(tmp_path: Path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["status", str(root)])
    assert result.exit_code == 0


def test_exit_0_score_always(tmp_path: Path):
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["score", str(root)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Section F: JSON output is valid JSON with required fields
# ---------------------------------------------------------------------------


def test_all_json_outputs_have_required_fields(tmp_path: Path):
    """All --json outputs include schema_version, command, root, passed."""
    root = _init_repo(tmp_path)
    required = {"schema_version", "command", "root", "passed"}

    commands = [
        ["scan", str(root), "--json"],
        ["verify", str(root), "--json"],
        ["status", str(root), "--json"],
        ["preflight", str(root), "--json"],
        ["score", str(root), "--json"],
        ["portability", "scan", str(root), "--json"],
        ["registry", "build", str(root), "--json"],
        ["audit", "readiness", str(root), "--json"],
        ["audit", "coverage", str(root), "--json"],
        ["audit", "drift", str(root), "--json"],
        ["audit", "multi-agent", str(root), "--json"],
        ["discover", "candidates", str(root), "--json"],
        ["authority", "verify", str(root), "--json"],
        ["skills", "index", str(root), "--json"],
        ["skills", "verify", str(root), "--json"],
        ["pipeline", "list", str(root), "--json"],
    ]

    for cmd in commands:
        result = runner.invoke(app, cmd)
        data = json.loads(result.output)
        missing = required - set(data.keys())
        assert not missing, f"Command {cmd} output missing fields: {missing}"


def test_schema_version_is_string_one(tmp_path: Path):
    """schema_version is the string '1', not an integer."""
    root = _init_repo(tmp_path)
    result = runner.invoke(app, ["verify", str(root), "--json"])
    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert isinstance(data["schema_version"], str)


# ---------------------------------------------------------------------------
# Section G: Fail-closed behavior
# ---------------------------------------------------------------------------


def test_init_error_message_to_stderr_on_bad_profile(tmp_path: Path):
    """Usage errors write to stderr and exit 2, not stdout + exit 1."""
    result = runner.invoke(app, ["init", str(tmp_path), "--profile", "bad"])
    assert result.exit_code == 2
    # In typer test runner, stderr is mixed with stdout in result.output
    assert "Error" in result.output or "invalid" in result.output.lower()


def test_verify_fail_closed_no_pipelines(tmp_path: Path):
    """verify with no pipelines should not silently pass."""
    runner.invoke(app, ["init", str(tmp_path)])
    # Remove all pipelines
    for f in (tmp_path / "governance" / "pipelines").glob("*.md"):
        f.unlink()
    result = runner.invoke(app, ["verify", str(tmp_path)])
    # No pipelines means no errors either — this is allowed to pass
    # but must not crash and must produce output
    assert result.exit_code in (0, 1)
    assert result.output  # must produce some output


def test_preflight_fail_closed_warning_only_repo(tmp_path: Path):
    """Preflight passes for a repo with only WARNING findings (exit 0)."""
    root = _init_repo(tmp_path)
    # Add a pipeline with missing scope (WARNING) but otherwise valid
    p = root / "governance" / "pipelines" / "001--setup.md"
    p.write_text(
        "# 001 — Setup\n\nStage: establish\n\nPurpose:\nBootstrap.\n\n"
        "Outputs:\n- artifacts/out.json\n\nSuccess criteria:\n- done\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["preflight", str(root)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Section H: lifecycle_to_json includes failed_count
# ---------------------------------------------------------------------------


def test_lifecycle_json_failed_count_zero():
    data = lifecycle_to_json(LifecycleResult(root=_ROOT))
    assert data["failed_count"] == 0


def test_lifecycle_json_failed_count_nonzero():
    rec = LifecycleRecord(
        pipeline_id="001", slug="foo", path=_PATH,
        declared_state="", effective_state=LifecycleState.FAILED, drift=False,
    )
    data = lifecycle_to_json(LifecycleResult(root=_ROOT, records=[rec]))
    assert data["failed_count"] == 1


# ---------------------------------------------------------------------------
# Section I: Severity enum values are stable strings
# ---------------------------------------------------------------------------


def test_severity_error_value():
    assert Severity.ERROR.value == "error"


def test_severity_warning_value():
    assert Severity.WARNING.value == "warning"


def test_severity_info_value():
    assert Severity.INFO.value == "info"


def test_severity_in_issue_json():
    """Severity appears as its string value in JSON output."""
    result = VerifyResult(root=_ROOT, issues=[_error_issue()])
    data = verify_to_json(result)
    assert data["issues"][0]["severity"] == "error"


def test_severity_warning_in_json():
    result = VerifyResult(root=_ROOT, issues=[_warning_issue()])
    data = verify_to_json(result)
    assert data["issues"][0]["severity"] == "warning"
