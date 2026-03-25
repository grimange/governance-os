"""Preflight governance check for governance-os.

Composes existing checks into a single fail-closed readiness gate:
- contract parsing
- schema and integrity validation
- dependency graph analysis
- portability checks
- authority validation (if requested)

Returns a unified pass/fail result with all issues.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from governance_os.models.issue import Issue, Severity


class PreflightResult(BaseModel):
    """Result of a preflight governance check."""

    root: Path
    checks: list[str] = []
    issues: list[Issue] = []

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def pipeline_count(self) -> int:
        return sum(1 for i in self.issues if i.pipeline_id is not None)
