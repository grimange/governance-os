"""Finding prioritization for governance-os.

Maps issue codes to priority levels (high/medium/low).
Priority is determined first by explicit code membership, then by severity fallback.
All mappings are listed explicitly — no hidden logic.
"""

from __future__ import annotations

from enum import StrEnum

from governance_os.models.issue import Issue, Severity


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# HIGH — codes that block or break governance integrity.
# Presence of any of these means something fundamental is broken.
_HIGH_CODES: frozenset[str] = frozenset(
    {
        "MISSING_REQUIRED_FIELD",
        "INVALID_STAGE",
        "DUPLICATE_PIPELINE_ID",
        "FILENAME_PARSE_ERROR",
        "MISSING_PIPELINES_DIR",
        "UNRESOLVED_DEPENDENCY",
        "DEPENDENCY_CYCLE",
        "ABSOLUTE_PATH",
        "WINDOWS_DRIVE_PATH",
        "HOME_RELATIVE_PATH",
        "PATH_TRAVERSAL",
        "AUTHORITY_MISSING_ROOT",
        "AUTHORITY_CONTRACT_IN_ARTIFACT_DIR",
        "AUTHORITY_CONFIG_INVALID",
        "REGISTRY_DUPLICATE_ID",
        "REGISTRY_FILE_MISSING",
        "REGISTRY_FILE_INVALID",
        "DOCTRINE_MISSING",
    }
)

# MEDIUM — codes that degrade governance quality but do not break it.
_MEDIUM_CODES: frozenset[str] = frozenset(
    {
        "AUDIT_MISSING_PURPOSE",
        "AUDIT_UNCONTRACTED_SURFACE",
        "AUDIT_MISSING_OUTPUT",
        "AUDIT_NO_PIPELINES",
        "AUTHORITY_PATH_DEPENDENCY",
        "AUTHORITY_CONFIG_DIR_MISSING",
        "REGISTRY_MISSING_STAGE",
        "REGISTRY_NO_OUTPUTS",
        "REGISTRY_STALE_ENTRY",
        "REGISTRY_UNTRACKED_PIPELINE",
        "DUPLICATE_SLUG",
        "EMPTY_LIST_ENTRY",
        "DUPLICATE_LIST_ENTRY",
        "DOCTRINE_EMPTY",
        "DOCTRINE_INCOMPLETE",
        "SKILLS_DUPLICATE_ID",
        "SKILLS_EMPTY_FILE",
    }
)

# LOW — informational / improvement opportunities.
# All INFO-severity codes not in HIGH or MEDIUM default to LOW.
_LOW_CODES: frozenset[str] = frozenset(
    {
        "AUDIT_MISSING_SCOPE",
        "AUDIT_WEAK_SUCCESS_CRITERIA",
        "AUDIT_MISSING_IMPL_NOTES",
        "AUDIT_NO_SURFACES_FOUND",
        "AUDIT_NO_DRIFT",
        "SKILLS_DIR_NOT_FOUND",
    }
)


def classify_priority(issue: Issue) -> Priority:
    """Return the priority level for *issue*.

    Lookup order:
    1. Explicit HIGH code membership.
    2. Explicit MEDIUM code membership.
    3. Explicit LOW code membership.
    4. Fallback: ERROR → HIGH, WARNING → MEDIUM, INFO → LOW.

    The fallback ensures unknown codes are still classified consistently.
    """
    if issue.code in _HIGH_CODES:
        return Priority.HIGH
    if issue.code in _MEDIUM_CODES:
        return Priority.MEDIUM
    if issue.code in _LOW_CODES:
        return Priority.LOW
    # Fallback by severity
    if issue.severity == Severity.ERROR:
        return Priority.HIGH
    if issue.severity == Severity.WARNING:
        return Priority.MEDIUM
    return Priority.LOW


def sort_by_priority(issues: list[Issue]) -> list[tuple[Priority, Issue]]:
    """Return (priority, issue) pairs sorted HIGH → MEDIUM → LOW."""
    order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    pairs = [(classify_priority(i), i) for i in issues]
    pairs.sort(key=lambda x: order[x[0]])
    return pairs
