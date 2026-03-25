"""High-level Python API for governance-os.

Provides stable, typed entry points that mirror the CLI command surface.
CLI commands should delegate to these functions rather than calling lower-level
modules directly.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.config import GovernanceConfig, load_config
from governance_os.discovery.pipelines import discover
from governance_os.graph.builder import build_graph
from governance_os.graph.analysis import detect_cycles
from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.status import StatusResult
from governance_os.parsing.filenames import FilenameParseError, parse_filenames
from governance_os.parsing.markdown_contract import ParseIssue, parse_contract
from governance_os.validation.integrity import validate_integrity
from governance_os.validation.portability import scan_pipelines
from governance_os.validation.schema import validate_pipelines
from governance_os.validation.status_logic import classify


# ---------------------------------------------------------------------------
# Internal assembly
# ---------------------------------------------------------------------------


def _parse_issue_to_issue(pi: ParseIssue) -> Issue:
    return Issue(
        code=pi.code,
        severity=Severity.ERROR,
        message=pi.message,
        path=pi.path,
    )


def _load_pipelines(
    root: Path,
    config: GovernanceConfig | None = None,
) -> tuple[list[Pipeline], list[Issue]]:
    """Discover, parse, and assemble Pipeline models from *root*.

    Returns:
        (pipelines, parse_errors) — parse_errors covers both filename and
        contract-level parse failures.
    """
    if config is None:
        config = load_config(root)

    discovery = discover(root, config)
    parse_errors: list[Issue] = []

    if discovery.missing_dir:
        parse_errors.append(Issue(
            code="MISSING_PIPELINES_DIR",
            severity=Severity.ERROR,
            message=(
                f"Pipelines directory not found: {discovery.pipelines_dir}. "
                "Run `govos init` to create the default structure."
            ),
            path=root,
        ))
        return [], parse_errors

    identities, filename_errors = parse_filenames(discovery.contracts)

    for fe in filename_errors:
        parse_errors.append(Issue(
            code="FILENAME_PARSE_ERROR",
            severity=Severity.ERROR,
            message=fe.reason,
            path=fe.path,
        ))

    pipelines: list[Pipeline] = []
    for identity in identities:
        contract = parse_contract(identity.path)

        # Promote contract-level parse issues to Issue records.
        for pi in contract.issues:
            parse_errors.append(_parse_issue_to_issue(pi))

        pipelines.append(Pipeline(
            numeric_id=identity.numeric_id,
            slug=identity.slug,
            path=identity.path,
            title=contract.title,
            stage=contract.stage,
            scope=contract.scope,
            purpose=contract.purpose,
            depends_on=contract.depends_on,
            inputs=contract.inputs,
            outputs=contract.outputs,
            implementation_notes=contract.implementation_notes,
            success_criteria=contract.success_criteria,
            out_of_scope=contract.out_of_scope,
        ))

    return pipelines, parse_errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan(root: Path | str, config: GovernanceConfig | None = None) -> ScanResult:
    """Discover and parse pipeline contracts under *root*.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.

    Returns:
        ScanResult with parsed pipelines and any parse errors.
    """
    root = Path(root)
    pipelines, parse_errors = _load_pipelines(root, config)
    return ScanResult(root=root, pipelines=pipelines, parse_errors=parse_errors)


def verify(root: Path | str, config: GovernanceConfig | None = None) -> VerifyResult:
    """Validate pipeline contracts and dependency graph under *root*.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.

    Returns:
        VerifyResult with all validation issues.
    """
    root = Path(root)
    pipelines, parse_errors = _load_pipelines(root, config)

    schema_issues = validate_pipelines(pipelines)
    integrity_issues = validate_integrity(pipelines)
    _, graph_issues = build_graph(pipelines)
    cycle_issues = detect_cycles(build_graph(pipelines)[0])

    all_issues = parse_errors + schema_issues + integrity_issues + graph_issues + cycle_issues

    return VerifyResult(root=root, pipelines=pipelines, issues=all_issues)


def status(root: Path | str, config: GovernanceConfig | None = None) -> StatusResult:
    """Classify pipeline readiness under *root*.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.

    Returns:
        StatusResult with readiness classification for each pipeline.
    """
    root = Path(root)
    pipelines, parse_errors = _load_pipelines(root, config)

    if not pipelines:
        from governance_os.models.status import StatusResult as _SR
        return _SR(root=root)

    integrity_issues = validate_integrity(pipelines)
    extra = parse_errors + integrity_issues

    return classify(pipelines, extra_issues=extra)


def portability(root: Path | str, config: GovernanceConfig | None = None) -> PortabilityResult:
    """Scan pipeline output declarations for portability issues under *root*.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.

    Returns:
        PortabilityResult with any non-portable path findings.
    """
    root = Path(root)
    pipelines, parse_errors = _load_pipelines(root, config)
    port_issues = scan_pipelines(pipelines)
    return PortabilityResult(root=root, issues=port_issues)
