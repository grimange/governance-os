"""Issue and severity models for governance-os."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Issue(BaseModel):
    """A structured diagnostic produced during parsing, validation, or analysis."""

    code: str
    severity: Severity
    message: str
    path: Path | None = None
    pipeline_id: str | None = None
    suggestion: str | None = None

    model_config = {"frozen": True}
