"""Issue and severity models for governance-os.

Severity semantics
------------------
Each Issue carries one of three severity levels.  Commands that validate or
enforce governance use the following contract:

ERROR   — Blocking finding.  The command exits 1.  Preflight, verify, audit,
          portability, authority, registry, and skills-verify all fail closed
          when any ERROR-severity issue is present.

WARNING — Advisory finding.  The command exits 0.  Warnings are surfaced in
          human and machine output so operators can act on them, but they do
          not block automation pipelines.

INFO    — Informational finding.  The command exits 0.  Purely advisory;
          no action required.

Exit code contract
------------------
0 — Pass: validation succeeded; no ERROR findings.
1 — Governance failure: one or more ERROR findings.
2 — Usage / input error: invalid argument, unrecognised resource, or
    bad profile/template combination.  Distinct from a governance failure
    so automation can distinguish "bad invocation" from "bad repo state".
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class Severity(StrEnum):
    """Severity levels for governance findings.

    Determines whether a command exits with success or failure:

    - ERROR   → blocks automation; command exits 1
    - WARNING → advisory only; command exits 0
    - INFO    → informational only; command exits 0
    """

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
    source: str | None = None  # e.g. "core", "authority", "codex_instructions"

    model_config = {"frozen": True}
