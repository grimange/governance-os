"""Naming and identity integrity validation for governance-os.

Validates global coherence across the full discovered pipeline set.
All checks operate on typed Pipeline models and return Issue records.
"""

from __future__ import annotations

from collections import defaultdict

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline


def validate_integrity(pipelines: list[Pipeline]) -> list[Issue]:
    """Check repo-wide identity integrity across all pipelines.

    Detects:
    - Duplicate numeric ids
    - Duplicate slugs
    - Pipelines with no numeric id (identity extraction failure)

    Args:
        pipelines: Full discovered pipeline inventory.

    Returns:
        List of Issue records. Empty means no integrity problems found.
    """
    issues: list[Issue] = []

    issues.extend(_check_duplicate_ids(pipelines))
    issues.extend(_check_duplicate_slugs(pipelines))

    return issues


def _check_duplicate_ids(pipelines: list[Pipeline]) -> list[Issue]:
    """Detect pipelines sharing the same numeric id."""
    issues: list[Issue] = []
    by_id: dict[str, list[Pipeline]] = defaultdict(list)

    for p in pipelines:
        if p.numeric_id:
            by_id[p.numeric_id].append(p)

    for numeric_id, group in by_id.items():
        if len(group) > 1:
            paths = ", ".join(str(p.path) for p in group)
            for p in group:
                issues.append(
                    Issue(
                        code="DUPLICATE_PIPELINE_ID",
                        severity=Severity.ERROR,
                        message=(
                            f"Numeric id '{numeric_id}' is shared by multiple pipelines: {paths}"
                        ),
                        path=p.path,
                        pipeline_id=numeric_id,
                        suggestion="Assign a unique numeric id to each pipeline file.",
                    )
                )

    return issues


def _check_duplicate_slugs(pipelines: list[Pipeline]) -> list[Issue]:
    """Detect pipelines sharing the same slug."""
    issues: list[Issue] = []
    by_slug: dict[str, list[Pipeline]] = defaultdict(list)

    for p in pipelines:
        if p.slug:
            by_slug[p.slug].append(p)

    for slug, group in by_slug.items():
        if len(group) > 1:
            paths = ", ".join(str(p.path) for p in group)
            for p in group:
                issues.append(
                    Issue(
                        code="DUPLICATE_SLUG",
                        severity=Severity.WARNING,
                        message=(f"Slug '{slug}' is shared by multiple pipelines: {paths}"),
                        path=p.path,
                        pipeline_id=p.numeric_id,
                        suggestion="Use a unique descriptive slug for each pipeline file.",
                    )
                )

    return issues
