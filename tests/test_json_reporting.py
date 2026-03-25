"""Tests for governance_os.reporting.json_report."""

import json
from pathlib import Path

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.status import PipelineStatus, StatusRecord, StatusResult
from governance_os.reporting.json_report import (
    portability_to_json,
    scan_to_json,
    status_to_json,
    to_json_str,
    verify_to_json,
)

_ROOT = Path("/repo")
_PATH = Path("001--foo.md")


def _pipeline():
    return Pipeline(
        numeric_id="001",
        slug="foo",
        path=_PATH,
        title="Foo",
        stage="establish",
    )


def _issue():
    return Issue(
        code="MISSING_STAGE",
        severity=Severity.ERROR,
        message="Missing stage",
        path=_PATH,
        pipeline_id="001",
    )


# --- scan ---


def test_scan_to_json_structure():
    result = ScanResult(root=_ROOT, pipelines=[_pipeline()])
    data = scan_to_json(result)
    assert data["command"] == "scan"
    assert data["root"] == str(_ROOT)
    assert data["total"] == 1
    assert len(data["pipelines"]) == 1
    assert data["parse_errors"] == []


def test_scan_to_json_pipeline_fields():
    data = scan_to_json(ScanResult(root=_ROOT, pipelines=[_pipeline()]))
    p = data["pipelines"][0]
    assert p["numeric_id"] == "001"
    assert p["slug"] == "foo"
    assert p["stage"] == "establish"


def test_scan_to_json_parse_errors():
    result = ScanResult(root=_ROOT, parse_errors=[_issue()])
    data = scan_to_json(result)
    assert len(data["parse_errors"]) == 1
    assert data["parse_errors"][0]["code"] == "MISSING_STAGE"


# --- verify ---


def test_verify_to_json_passed():
    result = VerifyResult(root=_ROOT, pipelines=[_pipeline()])
    data = verify_to_json(result)
    assert data["command"] == "verify"
    assert data["passed"] is True
    assert data["error_count"] == 0
    assert data["issues"] == []


def test_verify_to_json_failed():
    result = VerifyResult(root=_ROOT, issues=[_issue()])
    data = verify_to_json(result)
    assert data["passed"] is False
    assert data["error_count"] == 1
    assert data["issues"][0]["severity"] == "error"


# --- status ---


def test_status_to_json_structure():
    rec = StatusRecord(
        pipeline_id="001",
        slug="foo",
        path=_PATH,
        status=PipelineStatus.READY,
    )
    result = StatusResult(root=_ROOT, records=[rec])
    data = status_to_json(result)
    assert data["command"] == "status"
    assert data["total"] == 1
    assert data["records"][0]["status"] == "ready"


def test_status_to_json_reasons():
    rec = StatusRecord(
        pipeline_id="001",
        slug="foo",
        path=_PATH,
        status=PipelineStatus.BLOCKED,
        reasons=["Dep missing."],
    )
    result = StatusResult(root=_ROOT, records=[rec])
    data = status_to_json(result)
    assert data["records"][0]["reasons"] == ["Dep missing."]


# --- portability ---


def test_portability_to_json_passed():
    result = PortabilityResult(root=_ROOT)
    data = portability_to_json(result)
    assert data["command"] == "portability scan"
    assert data["passed"] is True
    assert data["issue_count"] == 0


def test_portability_to_json_failed():
    issue = Issue(
        code="ABSOLUTE_PATH",
        severity=Severity.ERROR,
        message="Bad path",
        path=_PATH,
        pipeline_id="001",
    )
    result = PortabilityResult(root=_ROOT, issues=[issue])
    data = portability_to_json(result)
    assert data["passed"] is False
    assert data["issue_count"] == 1


# --- to_json_str ---


def test_to_json_str_produces_valid_json():
    data = scan_to_json(ScanResult(root=_ROOT))
    s = to_json_str(data)
    parsed = json.loads(s)
    assert parsed["command"] == "scan"


def test_to_json_str_is_indented():
    data = {"key": "value"}
    s = to_json_str(data)
    assert "\n" in s


# --- issue serialisation ---


def test_issue_fields_present():
    result = VerifyResult(root=_ROOT, issues=[_issue()])
    data = verify_to_json(result)
    i = data["issues"][0]
    assert "code" in i
    assert "severity" in i
    assert "message" in i
    assert "path" in i
    assert "pipeline_id" in i
    assert "suggestion" in i
