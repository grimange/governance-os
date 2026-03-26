"""Lifecycle state models for governance-os pipeline contracts."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class LifecycleState(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


# States that indicate a pipeline cannot block downstream pipelines
_TERMINAL_CLEAR: frozenset[LifecycleState] = frozenset(
    {LifecycleState.COMPLETED, LifecycleState.ARCHIVED}
)

# States that block downstream pipelines
_BLOCKING_STATES: frozenset[LifecycleState] = frozenset(
    {LifecycleState.DRAFT, LifecycleState.BLOCKED, LifecycleState.FAILED}
)

# Valid declared-state strings (lower-case)
VALID_DECLARED_STATES: frozenset[str] = frozenset(s.value for s in LifecycleState)


class LifecycleRecord(BaseModel):
    """Lifecycle classification for a single pipeline."""

    pipeline_id: str
    slug: str
    path: Path
    declared_state: str  # raw value from contract (may be empty string)
    effective_state: LifecycleState
    drift: bool  # True when declared != effective (and declared is non-empty)
    reasons: list[str] = []

    model_config = {"frozen": True}


class LifecycleResult(BaseModel):
    """Aggregated lifecycle report for all discovered pipelines."""

    root: Path
    records: list[LifecycleRecord] = []

    def by_state(self, state: LifecycleState) -> list[LifecycleRecord]:
        return [r for r in self.records if r.effective_state == state]

    @property
    def active(self) -> list[LifecycleRecord]:
        return self.by_state(LifecycleState.ACTIVE)

    @property
    def blocked(self) -> list[LifecycleRecord]:
        return self.by_state(LifecycleState.BLOCKED)

    @property
    def failed(self) -> list[LifecycleRecord]:
        return self.by_state(LifecycleState.FAILED)

    @property
    def completed(self) -> list[LifecycleRecord]:
        return self.by_state(LifecycleState.COMPLETED)

    @property
    def draft(self) -> list[LifecycleRecord]:
        return self.by_state(LifecycleState.DRAFT)

    @property
    def ready(self) -> list[LifecycleRecord]:
        return self.by_state(LifecycleState.READY)

    @property
    def drifted(self) -> list[LifecycleRecord]:
        return [r for r in self.records if r.drift]
