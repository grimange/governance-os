"""Tests for the finding prioritization module."""

from pathlib import Path

import pytest

from governance_os.intelligence.priority import Priority, classify_priority, sort_by_priority
from governance_os.models.issue import Issue, Severity


def _issue(code: str, severity: Severity) -> Issue:
    return Issue(code=code, severity=severity, message="test")


# ---------------------------------------------------------------------------
# classify_priority — explicit HIGH codes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "MISSING_REQUIRED_FIELD",
        "DUPLICATE_PIPELINE_ID",
        "DEPENDENCY_CYCLE",
        "UNRESOLVED_DEPENDENCY",
        "ABSOLUTE_PATH",
        "AUTHORITY_MISSING_ROOT",
        "MISSING_PIPELINES_DIR",
        "DOCTRINE_MISSING",
    ],
)
def test_high_codes_always_high(code: str) -> None:
    issue = _issue(code, Severity.WARNING)  # even with non-ERROR severity
    assert classify_priority(issue) == Priority.HIGH


# ---------------------------------------------------------------------------
# classify_priority — explicit MEDIUM codes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "AUDIT_MISSING_PURPOSE",
        "AUDIT_UNCONTRACTED_SURFACE",
        "AUDIT_MISSING_OUTPUT",
        "REGISTRY_STALE_ENTRY",
        "AUTHORITY_PATH_DEPENDENCY",
    ],
)
def test_medium_codes_always_medium(code: str) -> None:
    issue = _issue(code, Severity.INFO)  # even with INFO severity
    assert classify_priority(issue) == Priority.MEDIUM


# ---------------------------------------------------------------------------
# classify_priority — explicit LOW codes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "AUDIT_MISSING_SCOPE",
        "AUDIT_WEAK_SUCCESS_CRITERIA",
        "AUDIT_MISSING_IMPL_NOTES",
        "AUDIT_NO_DRIFT",
        "AUDIT_NO_SURFACES_FOUND",
        "SKILLS_DIR_NOT_FOUND",
    ],
)
def test_low_codes_always_low(code: str) -> None:
    issue = _issue(code, Severity.WARNING)  # even with WARNING severity
    assert classify_priority(issue) == Priority.LOW


# ---------------------------------------------------------------------------
# classify_priority — fallback by severity for unknown codes
# ---------------------------------------------------------------------------


def test_unknown_error_code_fallback_high() -> None:
    issue = _issue("SOME_UNKNOWN_ERROR", Severity.ERROR)
    assert classify_priority(issue) == Priority.HIGH


def test_unknown_warning_code_fallback_medium() -> None:
    issue = _issue("SOME_UNKNOWN_WARNING", Severity.WARNING)
    assert classify_priority(issue) == Priority.MEDIUM


def test_unknown_info_code_fallback_low() -> None:
    issue = _issue("SOME_UNKNOWN_INFO", Severity.INFO)
    assert classify_priority(issue) == Priority.LOW


# ---------------------------------------------------------------------------
# sort_by_priority — ordering correctness
# ---------------------------------------------------------------------------


def test_sort_by_priority_ordering() -> None:
    issues = [
        _issue("AUDIT_MISSING_SCOPE", Severity.INFO),  # LOW
        _issue("MISSING_REQUIRED_FIELD", Severity.ERROR),  # HIGH
        _issue("AUDIT_MISSING_PURPOSE", Severity.WARNING),  # MEDIUM
    ]
    result = sort_by_priority(issues)
    priorities = [p.value for p, _ in result]
    assert priorities == ["high", "medium", "low"]


def test_sort_by_priority_stable_within_level() -> None:
    issues = [
        _issue("DUPLICATE_PIPELINE_ID", Severity.ERROR),
        _issue("DEPENDENCY_CYCLE", Severity.ERROR),
    ]
    result = sort_by_priority(issues)
    assert all(p == Priority.HIGH for p, _ in result)
    assert len(result) == 2


def test_sort_by_priority_empty() -> None:
    assert sort_by_priority([]) == []
