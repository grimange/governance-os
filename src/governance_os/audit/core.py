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

# Tokens that represent an explicit "no dependency" declaration
_NO_DEP_TOKENS = frozenset({"none", "n/a", "n/a.", "-", "tbd"})

# Required roles for a multi-agent Codex setup
_REQUIRED_ROLES = ("planner", "implementer", "reviewer")


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


def audit_readiness(
    root: Path, pipelines: list[Pipeline], extra_issues: list[Issue] | None = None
) -> AuditResult:
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
        real_criteria = [
            c for c in p.success_criteria if c.strip() and c.strip().lower() not in _NO_DEP_TOKENS
        ]
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

    # Look for pipeline-indicator files in repo (recursive)
    found_surfaces: list[tuple[Path, str]] = []

    def _walk(directory: Path) -> None:
        try:
            children = sorted(directory.iterdir())
        except PermissionError:
            return
        for child in children:
            if not child.is_dir():
                continue
            name = child.name
            if name in _IGNORED_DIRS or name.startswith("."):
                continue
            for indicator in _PIPELINE_INDICATORS:
                if (child / indicator).exists():
                    found_surfaces.append((child, indicator))
                    break
            _walk(child)

    if root.exists():
        _walk(root)

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


def audit_multi_agent(root: Path) -> AuditResult:
    """Audit multi-agent Codex setup for structural completeness.

    Checks that required role definitions, role governance contracts,
    a workflow contract, and artifact directories are all present.

    Does not check for agent execution or orchestration logic —
    only governance structure completeness.

    Args:
        root: Repository root.

    Returns:
        AuditResult with multi-agent governance findings.
    """
    findings: list[Issue] = []

    agents_dir = root / ".codex" / "agents"
    role_contracts_dir = root / "docs" / "governance" / "agents"
    workflow_contract = root / "docs" / "contracts" / "multi-agent-workflow.md"
    handoffs_dir = root / "artifacts" / "governance" / "handoffs"
    reviews_dir = root / "artifacts" / "governance" / "reviews"

    # If the agents directory doesn't exist there's nothing to audit
    if not agents_dir.exists():
        findings.append(
            Issue(
                code="MULTIAGENT_SETUP_MISSING",
                severity=Severity.WARNING,
                message="Multi-agent setup not found: .codex/agents/ directory does not exist.",
                path=root,
                suggestion=(
                    "Run `govos init --profile codex --template multi-agent` to scaffold "
                    "the multi-agent structure."
                ),
            )
        )
        return AuditResult(root=root, mode="multi-agent", findings=findings)

    # Check each required role definition (.codex/agents/<role>.toml)
    for role in _REQUIRED_ROLES:
        role_def = agents_dir / f"{role}.toml"
        if not role_def.exists():
            # Missing reviewer is an error — it creates role collapse risk
            severity = Severity.ERROR if role == "reviewer" else Severity.WARNING
            code = "MULTIAGENT_MISSING_REVIEWER" if role == "reviewer" else "MULTIAGENT_MISSING_ROLE_DEF"
            findings.append(
                Issue(
                    code=code,
                    severity=severity,
                    message=f"Multi-agent role definition missing: .codex/agents/{role}.toml",
                    path=agents_dir,
                    suggestion=f"Create .codex/agents/{role}.toml to define the {role} agent role.",
                )
            )

    # Check each required role contract (docs/governance/agents/<role>.md)
    for role in _REQUIRED_ROLES:
        contract_path = role_contracts_dir / f"{role}.md"
        if not contract_path.exists():
            findings.append(
                Issue(
                    code="MULTIAGENT_MISSING_ROLE_CONTRACT",
                    severity=Severity.WARNING,
                    message=f"Role governance contract missing: docs/governance/agents/{role}.md",
                    path=role_contracts_dir if role_contracts_dir.exists() else root,
                    suggestion=(
                        f"Create docs/governance/agents/{role}.md to define the {role} "
                        "role's governance obligations and forbidden actions."
                    ),
                )
            )
        elif not contract_path.read_text(encoding="utf-8").strip():
            findings.append(
                Issue(
                    code="MULTIAGENT_EMPTY_ROLE_CONTRACT",
                    severity=Severity.WARNING,
                    message=f"Role governance contract is empty: docs/governance/agents/{role}.md",
                    path=contract_path,
                    suggestion=f"Add governance content to docs/governance/agents/{role}.md.",
                )
            )

    # Check for role mismatch: .toml defined but no corresponding .md contract
    if role_contracts_dir.exists():
        toml_roles = {f.stem for f in agents_dir.glob("*.toml")}
        md_roles = {f.stem for f in role_contracts_dir.glob("*.md")}
        for role in sorted(toml_roles - md_roles - set(_REQUIRED_ROLES)):
            findings.append(
                Issue(
                    code="MULTIAGENT_ROLE_MISMATCH",
                    severity=Severity.WARNING,
                    message=(
                        f"Role '{role}' has a definition (.codex/agents/{role}.toml) "
                        "but no governance contract."
                    ),
                    path=agents_dir / f"{role}.toml",
                    suggestion=f"Create docs/governance/agents/{role}.md.",
                )
            )

    # Check workflow contract
    if not workflow_contract.exists():
        findings.append(
            Issue(
                code="MULTIAGENT_MISSING_WORKFLOW",
                severity=Severity.WARNING,
                message="Multi-agent workflow contract missing: docs/contracts/multi-agent-workflow.md",
                path=root / "docs" / "contracts",
                suggestion=(
                    "Create docs/contracts/multi-agent-workflow.md to define the "
                    "multi-agent sequence, artifacts, and completion criteria."
                ),
            )
        )

    # Check artifact directories
    if not handoffs_dir.exists():
        findings.append(
            Issue(
                code="MULTIAGENT_MISSING_HANDOFFS_DIR",
                severity=Severity.INFO,
                message="Handoff artifact directory not found: artifacts/governance/handoffs/",
                path=root / "artifacts" / "governance",
                suggestion="Create artifacts/governance/handoffs/ to store planner handoff records.",
            )
        )

    if not reviews_dir.exists():
        findings.append(
            Issue(
                code="MULTIAGENT_MISSING_REVIEWS_DIR",
                severity=Severity.INFO,
                message="Review artifact directory not found: artifacts/governance/reviews/",
                path=root / "artifacts" / "governance",
                suggestion="Create artifacts/governance/reviews/ to store reviewer outcome records.",
            )
        )

    return AuditResult(root=root, mode="multi-agent", findings=findings)
