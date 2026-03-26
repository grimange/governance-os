"""Canonical failure codes for governance-os governed runs.

Every governance violation is classified by one of these codes.
Codes are machine-readable and appear in ValidationResult, audit findings,
and trace completion records.

Failure codes are fail-closed: if governance conditions are not met, the run
is classified as invalid using the most specific applicable code.
"""

from __future__ import annotations

from enum import StrEnum


class FailureCode(StrEnum):
    """Canonical failure codes for governed MCP runs.

    Each code represents a distinct governance violation class.
    Codes are stable identifiers — do not rename without a deprecation cycle.
    """

    # Tool availability and policy
    TOOLING_UNAVAILABLE_FAIL_CLOSED = "TOOLING_UNAVAILABLE_FAIL_CLOSED"
    """Required governance tooling was unavailable; run cannot proceed."""

    TOOL_POLICY_VIOLATION = "TOOL_POLICY_VIOLATION"
    """A required tool was not called, or a forbidden tool was used."""

    TOOL_BYPASS_DETECTED = "TOOL_BYPASS_DETECTED"
    """A file change or action was performed outside the managed tool surface."""

    # Sequence and ordering
    SEQUENCE_VIOLATION = "SEQUENCE_VIOLATION"
    """Required tool call sequence was violated (e.g. finalize before patch)."""

    # Evidence and verification
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    """Required evidence was not recorded before finalization."""

    TEST_EXECUTION_MISSING = "TEST_EXECUTION_MISSING"
    """Test execution was required by policy but was not performed."""

    # Input validity
    CONTRACT_INPUT_INVALID = "CONTRACT_INPUT_INVALID"
    """A tool received an invalid or missing required input."""
