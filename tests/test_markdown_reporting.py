"""Tests for governance_os.reporting.markdown."""

from pathlib import Path

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.status import PipelineStatus, StatusRecord, StatusResult
from governance_os.reporting.markdown import (
    portability_report,
    scan_report,
    status_report,
    verify_report,
    write_report,
)

_ROOT = Path("/repo")
_PATH = Path("/repo/governance/pipelines/001--test.md")


def _make_pipeline(**kwargs) -> Pipeline:
    defaults = {
        "numeric_id": "001",
        "slug": "test",
        "path": _PATH,
        "title": "Test",
        "stage": "establish",
        "outputs": ["artifacts/out.json"],
        "success_criteria": ["done"],
    }
    defaults.update(kwargs)
    return Pipeline(**defaults)


def test_scan_report_empty():
    result = ScanResult(root=_ROOT)
    md = scan_report(result)
    assert "# Scan Report" in md
    assert "0" in md


def test_scan_report_with_pipelines():
    p = _make_pipeline()
    result = ScanResult(root=_ROOT, pipelines=[p])
    md = scan_report(result)
    assert "001" in md
    assert "test" in md
    assert "establish" in md


def test_scan_report_with_parse_errors():
    issue = Issue(code="FILENAME_PARSE_ERROR", severity=Severity.ERROR, message="Bad name.")
    result = ScanResult(root=_ROOT, parse_errors=[issue])
    md = scan_report(result)
    assert "Parse Errors" in md
    assert "FILENAME_PARSE_ERROR" in md


def test_verify_report_passed():
    p = _make_pipeline()
    result = VerifyResult(root=_ROOT, pipelines=[p])
    md = verify_report(result)
    assert "PASSED" in md
    assert "# Verify Report" in md


def test_verify_report_failed():
    issue = Issue(
        code="MISSING_REQUIRED_FIELD",
        severity=Severity.ERROR,
        message="Required field missing.",
    )
    result = VerifyResult(root=_ROOT, pipelines=[], issues=[issue])
    md = verify_report(result)
    assert "FAILED" in md
    assert "MISSING_REQUIRED_FIELD" in md


def test_status_report_with_records():
    record = StatusRecord(
        pipeline_id="001",
        slug="test",
        path=_PATH,
        status=PipelineStatus.READY,
    )
    result = StatusResult(root=_ROOT, records=[record])
    md = status_report(result)
    assert "# Status Report" in md
    assert "ready" in md
    assert "001" in md


def test_status_report_summary():
    records = [
        StatusRecord(pipeline_id="001", slug="a", path=_PATH, status=PipelineStatus.READY),
        StatusRecord(pipeline_id="002", slug="b", path=_PATH, status=PipelineStatus.BLOCKED),
    ]
    result = StatusResult(root=_ROOT, records=records)
    md = status_report(result)
    assert "ready: 1" in md
    assert "blocked: 1" in md


def test_portability_report_passed():
    result = PortabilityResult(root=_ROOT)
    md = portability_report(result)
    assert "PASSED" in md
    assert "# Portability Report" in md


def test_portability_report_failed():
    issue = Issue(
        code="ABSOLUTE_PATH",
        severity=Severity.ERROR,
        message="Output '/foo' is absolute.",
        path=_PATH,
        pipeline_id="001",
    )
    result = PortabilityResult(root=_ROOT, issues=[issue])
    md = portability_report(result)
    assert "FAILED" in md
    assert "ABSOLUTE_PATH" in md


def test_write_report(tmp_path: Path):
    out = tmp_path / "reports" / "out.md"
    write_report("# Hello", out)
    assert out.read_text() == "# Hello"
