"""JSON reporting for governance-os.

Converts typed result objects into stable, machine-readable JSON structures.
All serialisation goes through this module; CLI --json flags must not
build JSON ad hoc.
"""

from __future__ import annotations

import json
from typing import Any

from governance_os.audit.core import AuditResult
from governance_os.authority.core import AuthorityResult
from governance_os.discovery.candidates import CandidateResult
from governance_os.models.issue import Issue
from governance_os.models.pipeline import Pipeline
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.score import ScoreResult
from governance_os.models.status import StatusRecord, StatusResult
from governance_os.preflight.core import PreflightResult
from governance_os.registry.core import RegistryEntry, RegistryResult
from governance_os.skills.core import SkillEntry, SkillsResult

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


def _registry_entry(e: RegistryEntry) -> dict[str, Any]:
    return {
        "pipeline_id": e.pipeline_id,
        "slug": e.slug,
        "title": e.title,
        "stage": e.stage,
        "path": str(e.path),
        "depends_on": e.depends_on,
        "outputs_count": e.outputs_count,
    }


def _skill_entry(e: SkillEntry) -> dict[str, Any]:
    return {
        "skill_id": e.skill_id,
        "name": e.name,
        "path": str(e.path),
        "description": e.description,
    }


# ---------------------------------------------------------------------------
# New result serialisers
# ---------------------------------------------------------------------------


def registry_to_json(result: RegistryResult) -> dict[str, Any]:
    return {
        "command": "registry",
        "root": str(result.root),
        "passed": result.passed,
        "entry_count": result.entry_count,
        "entries": [_registry_entry(e) for e in result.entries],
        "issues": [_issue(i) for i in result.issues],
    }


def preflight_to_json(result: PreflightResult) -> dict[str, Any]:
    return {
        "command": "preflight",
        "root": str(result.root),
        "passed": result.passed,
        "checks": result.checks,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "issues": [_issue(i) for i in result.issues],
    }


def audit_to_json(result: AuditResult) -> dict[str, Any]:
    return {
        "command": f"audit {result.mode}",
        "root": str(result.root),
        "mode": result.mode,
        "passed": result.passed,
        "finding_count": result.finding_count,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "findings": [_issue(f) for f in result.findings],
    }


def authority_to_json(result: AuthorityResult) -> dict[str, Any]:
    return {
        "command": "authority verify",
        "root": str(result.root),
        "passed": result.passed,
        "issue_count": result.issue_count,
        "issues": [_issue(i) for i in result.issues],
    }


def candidates_to_json(result: CandidateResult) -> dict[str, Any]:
    candidates = []
    for c in result.candidates:
        try:
            rel = str(c.path.relative_to(result.root))
        except ValueError:
            rel = str(c.path)
        candidates.append(
            {
                "path": rel,
                "suggested_id": c.suggested_id,
                "confidence": c.confidence,
                "reason": c.reason,
            }
        )
    return {
        "command": "discover candidates",
        "root": str(result.root),
        "candidate_count": result.candidate_count,
        "candidates": candidates,
    }


def skills_to_json(result: SkillsResult) -> dict[str, Any]:
    return {
        "command": "skills",
        "root": str(result.root),
        "skills_dir": str(result.skills_dir) if result.skills_dir else None,
        "passed": result.passed,
        "skill_count": result.skill_count,
        "entries": [_skill_entry(e) for e in result.entries],
        "issues": [_issue(i) for i in result.issues],
    }


# ---------------------------------------------------------------------------
# Rendering helper
# ---------------------------------------------------------------------------


def score_to_json(result: ScoreResult) -> dict[str, Any]:
    categories = [
        {
            "name": c.name,
            "score": c.score,
            "finding_count": c.finding_count,
            "error_count": c.error_count,
            "warning_count": c.warning_count,
            "info_count": c.info_count,
            "deductions": c.deductions,
        }
        for c in result.categories
    ]

    prioritized = [
        {
            "priority": f.priority,
            "code": f.code,
            "severity": f.severity,
            "message": f.message,
            "path": f.path,
            "pipeline_id": f.pipeline_id,
            "suggestion": f.suggestion,
        }
        for f in result.prioritized_findings
    ]

    insights = [
        {
            "code": i.code,
            "title": i.title,
            "explanation": i.explanation,
            "priority": i.priority,
            "related_findings": i.related_findings,
        }
        for i in result.derived_insights
    ]

    delta = [
        {
            "category": d.category,
            "previous_score": d.previous_score,
            "current_score": d.current_score,
            "change": d.change,
        }
        for d in result.delta
    ]

    return {
        "command": "score",
        "root": str(result.root),
        "overall_score": result.overall_score,
        "grade": result.grade,
        "formula": result.formula_explanation,
        "categories": categories,
        "prioritized_findings": prioritized,
        "derived_insights": insights,
        "delta": delta,
    }


def to_json_str(data: dict[str, Any], *, indent: int = 2) -> str:
    """Serialise *data* to a JSON string."""
    return json.dumps(data, indent=indent, default=str)
