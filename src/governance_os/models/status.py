"""Pipeline status and readiness models for governance-os."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class PipelineStatus(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    INVALID = "invalid"
    ORPHANED = "orphaned"
    COMPLETE = "complete"


class StatusRecord(BaseModel):
    """Readiness classification for a single pipeline."""

    pipeline_id: str
    slug: str
    path: Path
    status: PipelineStatus
    reasons: list[str] = []

    model_config = {"frozen": True}


class StatusResult(BaseModel):
    """Aggregated readiness report for all discovered pipelines."""

    root: Path
    records: list[StatusRecord] = []

    def by_status(self, status: PipelineStatus) -> list[StatusRecord]:
        return [r for r in self.records if r.status == status]

    @property
    def ready(self) -> list[StatusRecord]:
        return self.by_status(PipelineStatus.READY)

    @property
    def blocked(self) -> list[StatusRecord]:
        return self.by_status(PipelineStatus.BLOCKED)

    @property
    def invalid(self) -> list[StatusRecord]:
        return self.by_status(PipelineStatus.INVALID)
