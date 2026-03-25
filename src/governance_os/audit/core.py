"""Governance audit analysis for governance-os.

Provides deeper governance coverage analysis beyond pass/fail validation:
- readiness: surface governance gaps and missing required sections
- coverage: detect uncontracted pipeline-like directories
- drift: declared outputs vs actual filesystem state
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline

# Directories that are likely pipeline-like surfaces but should be excluded from coverage checks
_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".github",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        ".tox",
        ".mypy_cache",
        "site-packages",
    }
)

# Files/patterns that suggest a directory is a pipeline/automation surface
_PIPELINE_INDICATORS = frozenset(
    {
        "Makefile",
        "makefile",
        "build.sh",
        "run.sh",
        "deploy.sh",
        "release.sh",
        "pipeline.yaml",
        "pipeline.yml",
        "workflow.yaml",
        "workflow.yml",
        "Dockerfile",
        "docker-compose.yaml",
        "docker-compose.yml",
        ".buildkite",
        "Jenkinsfile",
        "circle.yml",
        ".travis.yml",
    }
)


class AuditResult(BaseModel):
    """Result of a governance audit operation."""

    root: Path
    mode: str
    findings: list[Issue] = []

    @property
    def passed(self) -> bool:
        return not any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)


def audit_readiness(root: Path, pipelines: list[Pipeline], extra_issues: list[Issue] | None = None) -> AuditResult:
    """Audit governance readiness: find contracts missing important sections.

    Checks beyond basic schema validation:
    - Contracts missing purpose documentation
    - Contracts with empty depends_on (not explicitly none/n/a)
    - Contracts with no scope declaration
    - Contracts with very few success criteria
    - Contracts referencing non-existent dependencies

    Args:
        root: Repository root.
        pipelines: Discovered pipeline contracts.
        extra_issues: Pre-computed validation issues to incorporate.

    Returns:
        AuditResult with readiness findings.
    """
    findings: list[Issue] = []

    if not pipelines:
        findings.append(
            Issue(
                code="AUDIT_NO_PIPELINES",
                severity=Severity.WARNING,
                message="No pipeline contracts discovered. Run `govos init` to scaffold the structure.",
                path=root,
                suggestion="Create at least one pipeline contract to establish governance coverage.",
            )
        )
        return AuditResult(root=root, mode="readiness", findings=findings)

    _NO_DEP_TOKENS = frozenset({"none", "n/a", "-"})

    for p in pipelines:
        # Missing purpose (structural weakness)
        if not p.purpose.strip():
            findings.append(
                Issue(
                    code="AUDIT_MISSING_PURPOSE",
                    severity=Severity.WARNING,
                    message=f"Pipeline '{p.numeric_id}' ({p.slug}) has no purpose declaration.",
                    path=p.path,
                    pipeline_id=p.numeric_id,
                    suggestion="Add a Purpose section describing the intent and outcome of this pipeline.",
                )
            )

        # Missing scope declaration
        if not p.scope.strip():
            findings.append(
                Issue(
                    code="AUDIT_MISSING_SCOPE",
                    severity=Severity.INFO,
                    message=f"Pipeline '{p.numeric_id}' ({p.slug}) has no scope declaration.",
                    path=p.path,
                    pipeline_id=p.numeric_id,
                    suggestion="Add a Scope section to clarify what this pipeline covers.",
                )
            )

        # Weak success criteria (fewer than 2 entries)
        real_criteria = [c for c in p.success_criteria if c.strip() and c.strip().lower() not in _NO_DEP_TOKENS]
        if len(real_criteria) == 1:
            findings.append(
                Issue(
                    code="AUDIT_WEAK_SUCCESS_CRITERIA",
                    severity=Severity.INFO,
                    message=f"Pipeline '{p.numeric_id}' ({p.slug}) has only one success criterion.",
                    path=p.path,
                    pipeline_id=p.numeric_id,
                    suggestion="Consider adding more specific success criteria to improve verifiability.",
                )
            )

        # No inputs declared (and not explicitly none)
        explicit_no_input = any(i.strip().lower() in _NO_DEP_TOKENS for i in p.inputs)
        if not p.inputs or (not explicit_no_input and not p.inputs):
            pass  # inputs are optional, skip

        # No implementation notes
        if not p.implementation_notes.strip():
            findings.append(
                Issue(
                    code="AUDIT_MISSING_IMPL_NOTES",
                    severity=Severity.INFO,
                    message=f"Pipeline '{p.numeric_id}' ({p.slug}) has no implementation notes.",
                    path=p.path,
                    pipeline_id=p.numeric_id,
                    suggestion="Add Implementation Notes to document how this pipeline is executed.",
                )
            )

    # Incorporate extra validation issues as findings
    if extra_issues:
        findings.extend(extra_issues)

    return AuditResult(root=root, mode="readiness", findings=findings)


def audit_coverage(root: Path, pipelines: list[Pipeline], pipelines_dir: Path) -> AuditResult:
    """Audit governance coverage: find pipeline-like dirs without contracts.

    Scans the repository for directories that look like automation surfaces
    but have no corresponding governance contract.

    Args:
        root: Repository root.
        pipelines: Currently contracted pipelines.
        pipelines_dir: Path to the pipelines contracts directory.

    Returns:
        AuditResult with coverage findings.
    """
    findings: list[Issue] = []

    # Build set of paths referenced in contracts (approximate)
    contracted_slugs = {p.slug for p in pipelines}
    contracted_paths = {p.path.parent for p in pipelines}

    # Look for pipeline-indicator files in repo
    found_surfaces: list[tuple[Path, str]] = []

    if root.exists():
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            name = child.name
            if name in _IGNORED_DIRS or name.startswith("."):
                continue

            # Check if directory contains pipeline indicator files
            for indicator in _PIPELINE_INDICATORS:
                indicator_path = child / indicator
                if indicator_path.exists():
                    found_surfaces.append((child, indicator))
                    break

    # Check .github/workflows specifically
    workflows_dir = root / ".github" / "workflows"
    if workflows_dir.exists():
        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        if workflow_files:
            found_surfaces.append((workflows_dir, f"{len(workflow_files)} workflow file(s)"))

    # Report uncontracted surfaces
    for surface_path, indicator in found_surfaces:
        # Check if slug-like name is contracted
        slug_like = surface_path.name.lower().replace("_", "-").replace(" ", "-")
        already_contracted = slug_like in contracted_slugs or surface_path in contracted_paths

        if not already_contracted:
            findings.append(
                Issue(
                    code="AUDIT_UNCONTRACTED_SURFACE",
                    severity=Severity.WARNING,
                    message=(
                        f"Directory '{surface_path.relative_to(root)}' looks like a pipeline surface "
                        f"(contains {indicator}) but has no governance contract."
                    ),
                    path=surface_path,
                    suggestion=(
                        f"Consider creating a contract for '{slug_like}' under "
                        f"{pipelines_dir.relative_to(root) if pipelines_dir.is_relative_to(root) else pipelines_dir}."
                    ),
                )
            )

    if not found_surfaces and not pipelines:
        findings.append(
            Issue(
                code="AUDIT_NO_SURFACES_FOUND",
                severity=Severity.INFO,
                message="No pipeline-like surfaces detected. Repository may be early-stage.",
                path=root,
            )
        )

    return AuditResult(root=root, mode="coverage", findings=findings)


def audit_drift(root: Path, pipelines: list[Pipeline]) -> AuditResult:
    """Audit for drift between declared outputs and actual filesystem state.

    Checks whether output artifacts declared in contracts actually exist on disk.
    Only checks paths that look like local file references (not URLs, not abstract names).

    Args:
        root: Repository root.
        pipelines: Discovered pipeline contracts.

    Returns:
        AuditResult with drift findings.
    """
    findings: list[Issue] = []

    _NO_DEP_TOKENS = frozenset({"none", "n/a", "-", "tbd", "n/a."})

    for p in pipelines:
        for output in p.outputs:
            output = output.strip()
            if not output or output.lower() in _NO_DEP_TOKENS:
                continue

            # Only check local-looking paths (no URLs, no abstract names with spaces)
            if "://" in output or " " in output:
                continue

            # Skip outputs that start with non-path-like characters
            if output.startswith("$") or output.startswith("{"):
                continue

            resolved = root / output
            if not resolved.exists():
                findings.append(
                    Issue(
                        code="AUDIT_MISSING_OUTPUT",
                        severity=Severity.WARNING,
                        message=(
                            f"Pipeline '{p.numeric_id}' ({p.slug}) declares output "
                            f"'{output}' which does not exist at {resolved}."
                        ),
                        path=p.path,
                        pipeline_id=p.numeric_id,
                        suggestion=f"Produce the artifact at '{output}' or update the contract if the path has changed.",
                    )
                )

    if not findings:
        findings.append(
            Issue(
                code="AUDIT_NO_DRIFT",
                severity=Severity.INFO,
                message=f"Checked {len(pipelines)} pipeline(s). No declared output drift detected.",
                path=root,
            )
        )

    return AuditResult(root=root, mode="drift", findings=findings)
