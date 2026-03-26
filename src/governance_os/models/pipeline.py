"""Typed pipeline model for governance-os."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from governance_os.models.issue import Issue


class Pipeline(BaseModel):
    """A fully parsed and normalised pipeline contract."""

    # Identity (from filename)
    numeric_id: str  # e.g. "001"
    slug: str  # e.g. "establish-skeleton"
    path: Path

    # Metadata (from contract body)
    title: str = ""
    stage: str = ""
    scope: str = ""
    purpose: str = ""
    depends_on: list[str] = []  # list of numeric ids or slugs as declared
    inputs: list[str] = []
    outputs: list[str] = []
    implementation_notes: str = ""
    success_criteria: list[str] = []
    out_of_scope: list[str] = []

    # Lifecycle — declared state from contract (may be empty string)
    declared_state: str = ""

    # Attached parse/validation issues
    issues: list[Issue] = []

    model_config = {"frozen": False}

    @property
    def id(self) -> str:
        """Canonical string identifier (numeric_id)."""
        return self.numeric_id
