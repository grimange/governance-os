"""JSON reporting for governance-os.

Converts typed result objects into stable, machine-readable JSON structures.
All serialisation goes through this module; CLI --json flags must not
build JSON ad hoc.
"""

from __future__ import annotations

import json
from typing import Any

from governance_os.models.issue import Issue
from governance_os.models.pipeline import Pipeline
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.status import StatusRecord, StatusResult


# ---------------------------------------------------------------------------
# Primitive serialisers
# ---------------------------------------------------------------------------


def _issue(issue: Issue) -> dict[str, Any]:
    return {
        "code": issue.code,
        "severity": issue.severity.value,
        "message": issue.message,
        "path": str(issue.path) if issue.path else None,
        "pipeline_id": issue.pipeline_id,
        "suggestion": issue.suggestion,
    }


def _pipeline(p: Pipeline) -> dict[str, Any]:
    return {
        "numeric_id": p.numeric_id,
        "slug": p.slug,
        "path": str(p.path),
        "title": p.title,
        "stage": p.stage,
        "depends_on": p.depends_on,
        "outputs": p.outputs,
    }


def _status_record(r: StatusRecord) -> dict[str, Any]:
    return {
        "pipeline_id": r.pipeline_id,
        "slug": r.slug,
        "path": str(r.path),
        "status": r.status.value,
        "reasons": r.reasons,
    }


# ---------------------------------------------------------------------------
# Result serialisers
# ---------------------------------------------------------------------------


def scan_to_json(result: ScanResult) -> dict[str, Any]:
    return {
        "command": "scan",
        "root": str(result.root),
        "total": result.total,
        "pipelines": [_pipeline(p) for p in result.pipelines],
        "parse_errors": [_issue(e) for e in result.parse_errors],
    }


def verify_to_json(result: VerifyResult) -> dict[str, Any]:
    return {
        "command": "verify",
        "root": str(result.root),
        "passed": result.passed,
        "error_count": result.error_count,
        "pipeline_count": len(result.pipelines),
        "issues": [_issue(i) for i in result.issues],
    }


def status_to_json(result: StatusResult) -> dict[str, Any]:
    return {
        "command": "status",
        "root": str(result.root),
        "total": len(result.records),
        "records": [_status_record(r) for r in result.records],
    }


def portability_to_json(result: PortabilityResult) -> dict[str, Any]:
    return {
        "command": "portability scan",
        "root": str(result.root),
        "passed": result.passed,
        "issue_count": len(result.issues),
        "issues": [_issue(i) for i in result.issues],
    }


# ---------------------------------------------------------------------------
# Rendering helper
# ---------------------------------------------------------------------------


def to_json_str(data: dict[str, Any], *, indent: int = 2) -> str:
    """Serialise *data* to a JSON string."""
    return json.dumps(data, indent=indent, default=str)
