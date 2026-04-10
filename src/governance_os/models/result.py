"""Result models for governance-os scan, verify, and portability operations."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline


class ScanResult(BaseModel):
    """Result of a discovery + parse scan."""

    root: Path
    pipelines: list[Pipeline] = []
    parse_errors: list[Issue] = []

    @property
    def total(self) -> int:
        return len(self.pipelines) + len(self.parse_errors)

    @property
    def passed(self) -> bool:
        return len(self.parse_errors) == 0


class VerifyResult(BaseModel):
    """Result of a full contract validation pass."""

    root: Path
    pipelines: list[Pipeline] = []
    issues: list[Issue] = []

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def passed(self) -> bool:
        return self.error_count == 0


class PortabilityResult(BaseModel):
    """Result of a portability scan."""

    root: Path
    issues: list[Issue] = []

    @property
    def passed(self) -> bool:
        """True when no ERROR-severity findings are present.

        Consistent with VerifyResult.passed — only ERROR issues block.
        WARNING and INFO issues are advisory and do not cause failure.
        """
        return not any(i.severity == Severity.ERROR for i in self.issues)
