"""Pipeline registry builder and verifier for governance-os.

The registry is a structured snapshot of all discovered pipeline contracts.
It supports both human-readable and machine-readable output and detects
missing, duplicate, stale, or inconsistent registry entries.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline


class RegistryEntry(BaseModel):
    """A single entry in the pipeline registry."""

    pipeline_id: str
    slug: str
    title: str
    stage: str
    path: Path
    depends_on: list[str] = []
    outputs_count: int = 0

    model_config = {"frozen": True}


class RegistryResult(BaseModel):
    """Result of a registry build or verify operation."""

    root: Path
    entries: list[RegistryEntry] = []
    issues: list[Issue] = []

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def entry_count(self) -> int:
        return len(self.entries)


def build_registry(root: Path, pipelines: list[Pipeline]) -> RegistryResult:
    """Build a registry snapshot from discovered pipeline contracts.

    Args:
        root: Repository root directory.
        pipelines: Parsed and assembled pipeline list.

    Returns:
        RegistryResult with entries and any structural issues.
    """
    issues: list[Issue] = []
    entries: list[RegistryEntry] = []

    # Detect duplicate IDs in the registry
    by_id: dict[str, list[Pipeline]] = defaultdict(list)
    for p in pipelines:
        by_id[p.numeric_id].append(p)

    for pid, group in by_id.items():
        if len(group) > 1:
            paths = ", ".join(str(p.path.name) for p in group)
            issues.append(
                Issue(
                    code="REGISTRY_DUPLICATE_ID",
                    severity=Severity.ERROR,
                    message=f"Duplicate pipeline id '{pid}' found in: {paths}",
                    path=root,
                    pipeline_id=pid,
                    suggestion="Assign a unique numeric id to each pipeline contract.",
                )
            )

    # Detect pipelines missing stage (registry quality issue)
    for p in pipelines:
        if not p.stage:
            issues.append(
                Issue(
                    code="REGISTRY_MISSING_STAGE",
                    severity=Severity.WARNING,
                    message=f"Pipeline '{p.numeric_id}' ({p.slug}) has no stage declared.",
                    path=p.path,
                    pipeline_id=p.numeric_id,
                    suggestion="Add a Stage field to the contract.",
                )
            )

    # Detect pipelines with empty output declarations
    for p in pipelines:
        if not p.outputs:
            issues.append(
                Issue(
                    code="REGISTRY_NO_OUTPUTS",
                    severity=Severity.WARNING,
                    message=f"Pipeline '{p.numeric_id}' ({p.slug}) declares no outputs.",
                    path=p.path,
                    pipeline_id=p.numeric_id,
                    suggestion="Declare at least one output artifact in the contract.",
                )
            )

    for p in sorted(pipelines, key=lambda x: x.numeric_id):
        entries.append(
            RegistryEntry(
                pipeline_id=p.numeric_id,
                slug=p.slug,
                title=p.title,
                stage=p.stage,
                path=p.path,
                depends_on=list(p.depends_on),
                outputs_count=len(p.outputs),
            )
        )

    return RegistryResult(root=root, entries=entries, issues=issues)


def reconcile_registry(
    root: Path,
    pipelines: list[Pipeline],
    existing_path: Path,
) -> RegistryResult:
    """Reconcile live pipelines against a persisted registry snapshot.

    Detects entries present in the snapshot that are no longer discovered,
    and entries discovered that are absent from the snapshot.

    Args:
        root: Repository root directory.
        pipelines: Currently discovered pipelines.
        existing_path: Path to an existing registry JSON file.

    Returns:
        RegistryResult with reconciliation issues.
    """
    import json

    result = build_registry(root, pipelines)

    if not existing_path.exists():
        result.issues.append(
            Issue(
                code="REGISTRY_FILE_MISSING",
                severity=Severity.WARNING,
                message=f"Registry file not found at {existing_path}. Run `govos registry build --out` to create it.",
                path=existing_path,
            )
        )
        return result

    try:
        raw = json.loads(existing_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return RegistryResult(
            root=root,
            entries=result.entries,
            issues=[
                Issue(
                    code="REGISTRY_FILE_INVALID",
                    severity=Severity.ERROR,
                    message=f"Registry file is not valid JSON: {exc}",
                    path=existing_path,
                )
            ],
        )

    snapshot_ids: set[str] = {e["pipeline_id"] for e in raw.get("entries", [])}
    live_ids: set[str] = {e.pipeline_id for e in result.entries}

    issues = list(result.issues)

    for missing_id in snapshot_ids - live_ids:
        issues.append(
            Issue(
                code="REGISTRY_STALE_ENTRY",
                severity=Severity.WARNING,
                message=f"Registry entry '{missing_id}' exists in snapshot but is no longer discovered.",
                path=existing_path,
                pipeline_id=missing_id,
                suggestion="Re-run `govos registry build` to refresh the snapshot.",
            )
        )

    for new_id in live_ids - snapshot_ids:
        issues.append(
            Issue(
                code="REGISTRY_UNTRACKED_PIPELINE",
                severity=Severity.WARNING,
                message=f"Pipeline '{new_id}' is discovered but absent from the registry snapshot.",
                path=root,
                pipeline_id=new_id,
                suggestion="Re-run `govos registry build --out` to update the snapshot.",
            )
        )

    return RegistryResult(root=root, entries=result.entries, issues=issues)
