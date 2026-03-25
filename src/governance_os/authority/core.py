"""Authority and source-of-truth validation for governance-os.

Validates that the repository treats the right files as authoritative sources
and does not inadvertently treat generated artifacts as governance roots.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline

# Files that should exist at the root for minimal governance authority
_REQUIRED_AUTHORITY_FILES = [
    "governance.yaml",
]

# Patterns for files that are typically generated artifacts and should not
# be referenced as authoritative sources of governance truth
_GENERATED_PATTERNS = frozenset(
    {
        "artifacts/",
        ".cache/",
        "dist/",
        "build/",
        "__pycache__/",
        ".ruff_cache/",
        ".pytest_cache/",
        "node_modules/",
    }
)


class AuthorityResult(BaseModel):
    """Result of an authority validation check."""

    root: Path
    issues: list[Issue] = []

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def verify_authority(root: Path, pipelines: list[Pipeline]) -> AuthorityResult:
    """Validate authority and source-of-truth configuration.

    Checks:
    - Required authoritative root files exist
    - Pipeline contracts are not inside artifact directories
    - Governance configuration is internally self-consistent
    - Contracts reference dependencies by id, not by path

    Args:
        root: Repository root directory.
        pipelines: Discovered and parsed pipeline contracts.

    Returns:
        AuthorityResult with any authority issues.
    """
    issues: list[Issue] = []

    # Check required authority files exist
    for filename in _REQUIRED_AUTHORITY_FILES:
        authority_file = root / filename
        if not authority_file.exists():
            issues.append(
                Issue(
                    code="AUTHORITY_MISSING_ROOT",
                    severity=Severity.ERROR,
                    message=f"Required authority file '{filename}' is missing from repo root.",
                    path=root / filename,
                    suggestion=f"Run `govos init` to create '{filename}', or create it manually.",
                )
            )

    # Check no pipeline contracts live inside artifact/generated directories
    for p in pipelines:
        try:
            rel = p.path.relative_to(root)
        except ValueError:
            continue

        for pattern in _GENERATED_PATTERNS:
            if str(rel).startswith(pattern):
                issues.append(
                    Issue(
                        code="AUTHORITY_CONTRACT_IN_ARTIFACT_DIR",
                        severity=Severity.ERROR,
                        message=(
                            f"Pipeline contract '{rel}' is inside an artifact/generated directory '{pattern}'. "
                            "Contracts must be authoritative source files, not generated artifacts."
                        ),
                        path=p.path,
                        pipeline_id=p.numeric_id,
                        suggestion="Move the contract to the designated pipelines directory.",
                    )
                )
                break

    # Check for contracts that appear to reference other contracts by path
    for p in pipelines:
        for dep in p.depends_on:
            dep_stripped = dep.strip()
            if dep_stripped.endswith(".md") or "/" in dep_stripped or "\\" in dep_stripped:
                issues.append(
                    Issue(
                        code="AUTHORITY_PATH_DEPENDENCY",
                        severity=Severity.WARNING,
                        message=(
                            f"Pipeline '{p.numeric_id}' ({p.slug}) references dependency "
                            f"'{dep_stripped}' by path rather than by numeric id."
                        ),
                        path=p.path,
                        pipeline_id=p.numeric_id,
                        suggestion="Use numeric ids (e.g. '001') to reference dependencies, not file paths.",
                    )
                )

    # Check governance.yaml consistency if it exists
    gov_yaml = root / "governance.yaml"
    if gov_yaml.exists():
        issues.extend(_check_config_consistency(root, gov_yaml, pipelines))

    return AuthorityResult(root=root, issues=issues)


def _check_config_consistency(root: Path, config_path: Path, pipelines: list[Pipeline]) -> list[Issue]:
    """Check governance.yaml is internally consistent with repo state."""
    import yaml

    issues: list[Issue] = []

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        issues.append(
            Issue(
                code="AUTHORITY_CONFIG_INVALID",
                severity=Severity.ERROR,
                message=f"governance.yaml is not valid YAML: {exc}",
                path=config_path,
                suggestion="Fix the YAML syntax in governance.yaml.",
            )
        )
        return issues

    # Check configured pipelines_dir actually exists
    pipelines_dir_str = raw.get("pipelines_dir", "")
    if pipelines_dir_str:
        declared_dir = root / pipelines_dir_str
        if not declared_dir.exists():
            issues.append(
                Issue(
                    code="AUTHORITY_CONFIG_DIR_MISSING",
                    severity=Severity.WARNING,
                    message=f"governance.yaml declares pipelines_dir='{pipelines_dir_str}' but that directory does not exist.",
                    path=config_path,
                    suggestion=f"Create the directory '{pipelines_dir_str}' or update governance.yaml.",
                )
            )

    return issues
