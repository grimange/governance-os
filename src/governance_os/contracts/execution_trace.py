"""Execution trace schema for governance-os governed MCP runs.

An ExecutionTrace records every tool call, file change, evidence reference,
and lifecycle transition that occurs during a governed run.

Traces are the evidence base for post-run validation. A run without a
complete trace cannot be validated and will be classified as invalid.

Persistence: traces are written to
  artifacts/governance/mcp-runs/<run_id>/trace.json
within the governed repository, making them durable and reviewable.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ToolCallRecord(BaseModel):
    """A single governed tool call recorded in the execution trace."""

    tool_name: str
    """MCP tool name as registered on the server."""

    order: int
    """Zero-based call order within the run (monotonically increasing)."""

    called_at: datetime = Field(default_factory=_utcnow)
    """UTC timestamp of the call."""

    result_ok: bool = True
    """Whether the tool returned a successful result."""

    inputs: dict = Field(default_factory=dict)
    """Sanitised input parameters (no secrets/credentials)."""

    model_config = {"frozen": True}


class FileChangeRecord(BaseModel):
    """A file change observed or performed during the run."""

    path: str
    """Repository-relative path of the changed file."""

    via_managed_patch: bool
    """True if the change was applied via govos_write_patch; False otherwise.

    Changes with via_managed_patch=False are potential TOOL_BYPASS_DETECTED
    violations depending on the active policy.
    """

    changed_at: datetime = Field(default_factory=_utcnow)
    """UTC timestamp of the change."""

    patch_id: str | None = None
    """Identifier of the managed patch, if applicable."""

    model_config = {"frozen": True}


class LifecycleStage(str):
    """MCP run lifecycle stages (Phase 5 — not StrEnum to remain JSON-serializable)."""

    TASK_LOADED = "TASK_LOADED"
    CONTEXT_ACQUIRED = "CONTEXT_ACQUIRED"
    CHANGES_APPLIED = "CHANGES_APPLIED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    EVIDENCE_RECORDED = "EVIDENCE_RECORDED"
    RESULT_FINALIZED = "RESULT_FINALIZED"


# Ordered lifecycle progression
LIFECYCLE_ORDER: list[str] = [
    LifecycleStage.TASK_LOADED,
    LifecycleStage.CONTEXT_ACQUIRED,
    LifecycleStage.CHANGES_APPLIED,
    LifecycleStage.VERIFICATION_COMPLETED,
    LifecycleStage.EVIDENCE_RECORDED,
    LifecycleStage.RESULT_FINALIZED,
]


class ExecutionTrace(BaseModel):
    """Complete record of a governed MCP run.

    Built up incrementally as tools are called. Validated at finalization.
    Persisted at artifacts/governance/mcp-runs/<run_id>/trace.json.
    """

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for this governed run."""

    pipeline_id: str | None = None
    """Pipeline contract being worked on, if applicable."""

    policy_mode: str = "standard_code_change"
    """Mode of the governing ToolPolicy in effect for this run."""

    started_at: datetime = Field(default_factory=_utcnow)
    """UTC timestamp when the run was initiated."""

    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    """All governed tool calls in call order."""

    file_changes: list[FileChangeRecord] = Field(default_factory=list)
    """All file changes observed during the run."""

    evidence_refs: list[str] = Field(default_factory=list)
    """Evidence references recorded via govos_record_evidence."""

    lifecycle_stage: str = LifecycleStage.TASK_LOADED
    """Current MCP run lifecycle stage."""

    finalized: bool = False
    """True once govos_finalize_result has been accepted."""

    finalized_at: datetime | None = None
    """UTC timestamp of finalization, if finalized."""

    finalization_summary: str = ""
    """Summary provided at finalization."""

    validation_passed: bool | None = None
    """Validation result at finalization time. None = not yet validated."""

    model_config = {"frozen": False}

    # ------------------------------------------------------------------
    # Mutation helpers (trace is mutable until finalized)
    # ------------------------------------------------------------------

    def record_tool_call(
        self,
        tool_name: str,
        inputs: dict | None = None,
        result_ok: bool = True,
    ) -> None:
        """Append a ToolCallRecord to the trace."""
        if self.finalized:
            raise RuntimeError(f"Cannot record tool call on finalized trace {self.run_id}.")
        self.tool_calls.append(
            ToolCallRecord(
                tool_name=tool_name,
                order=len(self.tool_calls),
                result_ok=result_ok,
                inputs=inputs or {},
            )
        )

    def record_file_change(
        self,
        path: str,
        *,
        via_managed_patch: bool,
        patch_id: str | None = None,
    ) -> None:
        """Append a FileChangeRecord to the trace."""
        if self.finalized:
            raise RuntimeError(f"Cannot record file change on finalized trace {self.run_id}.")
        self.file_changes.append(
            FileChangeRecord(
                path=path,
                via_managed_patch=via_managed_patch,
                patch_id=patch_id,
            )
        )

    def add_evidence(self, ref: str) -> None:
        """Append an evidence reference to the trace."""
        if self.finalized:
            raise RuntimeError(f"Cannot add evidence to finalized trace {self.run_id}.")
        self.evidence_refs.append(ref)

    def advance_lifecycle(self, stage: str) -> None:
        """Advance lifecycle stage (monotonically; regressions are no-ops)."""
        current_idx = LIFECYCLE_ORDER.index(self.lifecycle_stage) if self.lifecycle_stage in LIFECYCLE_ORDER else 0
        new_idx = LIFECYCLE_ORDER.index(stage) if stage in LIFECYCLE_ORDER else 0
        if new_idx > current_idx:
            self.lifecycle_stage = stage

    def tool_names_called(self) -> list[str]:
        """Return ordered list of tool names called in this run."""
        return [tc.tool_name for tc in self.tool_calls]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _trace_path(root: Path, run_id: str) -> Path:
        return root / "artifacts" / "governance" / "mcp-runs" / run_id / "trace.json"

    def save(self, root: Path) -> Path:
        """Persist trace to disk. Returns the path written."""
        p = self._trace_path(root, self.run_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            self.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return p

    @classmethod
    def load(cls, root: Path, run_id: str) -> "ExecutionTrace":
        """Load a trace from disk. Raises FileNotFoundError if absent."""
        p = cls._trace_path(root, run_id)
        return cls.model_validate_json(p.read_text(encoding="utf-8"))

    @classmethod
    def exists(cls, root: Path, run_id: str) -> bool:
        """Check whether a trace exists on disk."""
        return cls._trace_path(root, run_id).exists()
