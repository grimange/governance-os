"""Contract structure and allowed-value validation for governance-os.

Operates on typed Pipeline models and returns Issue records.
All issue codes are stable for consumption by both humans and Codex.
"""

from __future__ import annotations

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline

ALLOWED_STAGES: frozenset[str] = frozenset(
    {"establish", "implement", "verify", "report", "release"}
)

# Required non-empty fields and their human labels.
_REQUIRED_TEXT_FIELDS: list[tuple[str, str]] = [
    ("title", "title"),
    ("stage", "stage"),
    ("purpose", "purpose"),
]

_REQUIRED_LIST_FIELDS: list[tuple[str, str]] = [
    ("outputs", "outputs"),
    ("success_criteria", "success_criteria"),
]


def validate_pipeline(pipeline: Pipeline) -> list[Issue]:
    """Validate a single pipeline contract against schema rules.

    Args:
        pipeline: Typed pipeline model to validate.

    Returns:
        List of Issue records. Empty list means the pipeline is valid.
    """
    issues: list[Issue] = []
    pid = pipeline.numeric_id
    path = pipeline.path

    # --- Required text fields ---
    for field_name, label in _REQUIRED_TEXT_FIELDS:
        val = getattr(pipeline, field_name, "")
        if not val or not str(val).strip():
            issues.append(
                Issue(
                    code="MISSING_REQUIRED_FIELD",
                    severity=Severity.ERROR,
                    message=f"Required field '{label}' is missing or empty.",
                    path=path,
                    pipeline_id=pid,
                    suggestion=f"Add a non-empty '{label}' section to the contract.",
                )
            )

    # --- Required list fields ---
    for field_name, label in _REQUIRED_LIST_FIELDS:
        val: list[str] = getattr(pipeline, field_name, [])
        if not val:
            issues.append(
                Issue(
                    code="MISSING_REQUIRED_FIELD",
                    severity=Severity.ERROR,
                    message=f"Required field '{label}' is missing or empty.",
                    path=path,
                    pipeline_id=pid,
                    suggestion=f"Add at least one entry to the '{label}' section.",
                )
            )

    # --- Stage value ---
    if pipeline.stage and pipeline.stage not in ALLOWED_STAGES:
        issues.append(
            Issue(
                code="INVALID_STAGE",
                severity=Severity.ERROR,
                message=(
                    f"Stage '{pipeline.stage}' is not in the allowed set: "
                    + ", ".join(sorted(ALLOWED_STAGES))
                ),
                path=path,
                pipeline_id=pid,
                suggestion=f"Change stage to one of: {', '.join(sorted(ALLOWED_STAGES))}.",
            )
        )

    # --- Dependency list shape ---
    issues.extend(_validate_list_field(pipeline, "depends_on", pid))

    # --- Output list shape ---
    issues.extend(_validate_list_field(pipeline, "outputs", pid))

    return issues


def _validate_list_field(pipeline: Pipeline, field_name: str, pid: str) -> list[Issue]:
    """Check a list field for empty entries and duplicates."""
    issues: list[Issue] = []
    items: list[str] = getattr(pipeline, field_name, [])
    path = pipeline.path

    seen: set[str] = set()
    for item in items:
        if not item.strip():
            issues.append(
                Issue(
                    code="EMPTY_LIST_ENTRY",
                    severity=Severity.WARNING,
                    message=f"Empty entry found in '{field_name}'.",
                    path=path,
                    pipeline_id=pid,
                )
            )
            continue
        normalised = item.strip().lower()
        if normalised in seen:
            issues.append(
                Issue(
                    code="DUPLICATE_LIST_ENTRY",
                    severity=Severity.WARNING,
                    message=f"Duplicate entry '{item.strip()}' in '{field_name}'.",
                    path=path,
                    pipeline_id=pid,
                )
            )
        seen.add(normalised)

    return issues


def validate_pipelines(pipelines: list[Pipeline]) -> list[Issue]:
    """Validate a collection of pipelines and return all issues.

    Args:
        pipelines: List of typed pipeline models.

    Returns:
        Flat list of all Issue records across all pipelines.
    """
    issues: list[Issue] = []
    for pipeline in pipelines:
        issues.extend(validate_pipeline(pipeline))
    return issues
