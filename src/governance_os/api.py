"""High-level Python API for governance-os.

Provides stable, typed entry points that mirror the CLI command surface.
CLI commands should delegate to these functions rather than calling lower-level
modules directly.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.audit.core import (
    AuditResult,
    audit_coverage,
    audit_drift,
    audit_multi_agent,
    audit_readiness,
)
from governance_os.authority.core import AuthorityResult, verify_authority
from governance_os.config import GovernanceConfig, load_config
from governance_os.config.loader import resolve_pipelines_dir
from governance_os.discovery.candidates import CandidateResult, discover_candidates
from governance_os.discovery.pipelines import discover
from governance_os.graph.analysis import detect_cycles
from governance_os.graph.builder import build_graph
from governance_os.intelligence.comparison import compute_deltas
from governance_os.intelligence.insights import derive_insights
from governance_os.intelligence.priority import sort_by_priority
from governance_os.intelligence.scoring import (
    FORMULA_EXPLANATION,
    grade,
    overall_score,
    score_category,
)
from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.score import PrioritizedFinding, ScoreResult
from governance_os.models.status import StatusResult
from governance_os.parsing.filenames import parse_filenames
from governance_os.parsing.markdown_contract import ParseIssue, parse_contract
from governance_os.plugins.registry import run_plugin_checks
from governance_os.preflight.core import PreflightResult
from governance_os.profiles.definitions import ProfileDefinition
from governance_os.profiles.registry import (
    list_profiles,
    resolve_profile,
    validate_profile_surfaces,
)
from governance_os.registry.core import RegistryResult, build_registry, reconcile_registry
from governance_os.skills.core import SkillsResult, index_skills, verify_skills
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
        parse_errors.append(
            Issue(
                code="MISSING_PIPELINES_DIR",
                severity=Severity.ERROR,
                message=(
                    f"Pipelines directory not found: {discovery.pipelines_dir}. "
                    "Run `govos init` to create the default structure."
                ),
                path=root,
            )
        )
        return [], parse_errors

    identities, filename_errors = parse_filenames(discovery.contracts)

    for fe in filename_errors:
        parse_errors.append(
            Issue(
                code="FILENAME_PARSE_ERROR",
                severity=Severity.ERROR,
                message=fe.reason,
                path=fe.path,
            )
        )

    pipelines: list[Pipeline] = []
    for identity in identities:
        contract = parse_contract(identity.path)

        # Promote contract-level parse issues to Issue records.
        for pi in contract.issues:
            parse_errors.append(_parse_issue_to_issue(pi))

        pipelines.append(
            Pipeline(
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
            )
        )

    return pipelines, parse_errors


# ---------------------------------------------------------------------------
# Public API — original commands
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
    graph, graph_issues = build_graph(pipelines)
    cycle_issues = detect_cycles(graph)

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
        return StatusResult(root=root)

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


# ---------------------------------------------------------------------------
# Public API — registry commands
# ---------------------------------------------------------------------------


def registry_build(root: Path | str, config: GovernanceConfig | None = None) -> RegistryResult:
    """Build a registry snapshot from all discovered pipeline contracts.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.

    Returns:
        RegistryResult with entries and structural issues.
    """
    root = Path(root)
    pipelines, parse_errors = _load_pipelines(root, config)
    result = build_registry(root, pipelines)
    # Incorporate parse errors as registry issues
    if parse_errors:
        result = RegistryResult(
            root=root,
            entries=result.entries,
            issues=parse_errors + result.issues,
        )
    return result


def registry_verify(
    root: Path | str,
    registry_path: Path | None = None,
    config: GovernanceConfig | None = None,
) -> RegistryResult:
    """Verify registry integrity, optionally reconciling against a snapshot.

    Args:
        root: Repo root directory.
        registry_path: Optional path to an existing registry JSON snapshot.
        config: Optional pre-loaded config.

    Returns:
        RegistryResult with integrity issues.
    """
    root = Path(root)
    pipelines, parse_errors = _load_pipelines(root, config)

    if registry_path is not None:
        result = reconcile_registry(root, pipelines, registry_path)
    else:
        result = build_registry(root, pipelines)

    if parse_errors:
        result = RegistryResult(
            root=root,
            entries=result.entries,
            issues=parse_errors + result.issues,
        )
    return result


# ---------------------------------------------------------------------------
# Public API — preflight command
# ---------------------------------------------------------------------------


def preflight(
    root: Path | str,
    config: GovernanceConfig | None = None,
    include_authority: bool = False,
    include_portability: bool = True,
) -> PreflightResult:
    """Run a fail-closed preflight governance readiness check.

    Composes: contract parsing, schema validation, integrity, graph analysis,
    portability (optional), authority (optional), and active plugin checks.

    Plugin activation is driven by:
      - the `profile` field in config (or "generic" default)
      - `enabled_plugins` / `disabled_plugins` in config

    For the `codex` profile, `codex_instructions` is active by default.
    Plugin checks are additive — they do not replace core checks.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.
        include_authority: Run authority validation explicitly. Also activates
            the authority plugin if not already in the active plugin set.
        include_portability: Run portability checks (default True).

    Returns:
        PreflightResult with all issues and pass/fail status.
    """
    root = Path(root)
    if config is None:
        config = load_config(root)

    checks: list[str] = []
    all_issues: list[Issue] = []

    # 1. Parse contracts
    pipelines, parse_errors = _load_pipelines(root, config)
    checks.append("contract-parsing")
    all_issues.extend(parse_errors)

    # 2. Schema validation
    schema_issues = validate_pipelines(pipelines)
    checks.append("schema-validation")
    all_issues.extend(schema_issues)

    # 3. Integrity
    integrity_issues = validate_integrity(pipelines)
    checks.append("integrity")
    all_issues.extend(integrity_issues)

    # 4. Dependency graph
    graph, graph_issues = build_graph(pipelines)
    cycle_issues = detect_cycles(graph)
    checks.append("dependency-graph")
    all_issues.extend(graph_issues)
    all_issues.extend(cycle_issues)

    # 5. Portability
    if include_portability:
        port_issues = scan_pipelines(pipelines)
        checks.append("portability")
        all_issues.extend(port_issues)

    # 6. Authority (explicit flag — legacy path, kept for backward compatibility)
    if include_authority:
        auth_result = verify_authority(root, pipelines)
        checks.append("authority")
        all_issues.extend(auth_result.issues)

    # 7. Plugin checks (profile-driven, additive)
    #    Exclude "authority" plugin if already run via include_authority to avoid duplication.
    disabled = list(config.disabled_plugins)
    if include_authority and "authority" not in disabled:
        disabled.append("authority")

    plugin_check_names, plugin_issues = run_plugin_checks(
        root,
        pipelines,
        profile_id=config.profile,
        enabled_plugins=config.enabled_plugins,
        disabled_plugins=disabled,
    )
    checks.extend(plugin_check_names)
    all_issues.extend(plugin_issues)

    return PreflightResult(root=root, checks=checks, issues=all_issues)


# ---------------------------------------------------------------------------
# Public API — audit commands
# ---------------------------------------------------------------------------


def audit(
    root: Path | str,
    mode: str = "readiness",
    config: GovernanceConfig | None = None,
) -> AuditResult:
    """Run a governance audit in the specified mode.

    Args:
        root: Repo root directory.
        mode: Audit mode — "readiness", "coverage", or "drift".
        config: Optional pre-loaded config.

    Returns:
        AuditResult with governance findings.

    Raises:
        ValueError: If mode is not one of the supported values.
    """
    root = Path(root)
    if config is None:
        config = load_config(root)

    supported = {"readiness", "coverage", "drift", "multi-agent"}
    if mode not in supported:
        raise ValueError(
            f"Unsupported audit mode '{mode}'. Supported: {', '.join(sorted(supported))}"
        )

    if mode == "multi-agent":
        return audit_multi_agent(root)

    pipelines, parse_errors = _load_pipelines(root, config)

    if mode == "readiness":
        return audit_readiness(root, pipelines, extra_issues=parse_errors)

    if mode == "coverage":
        pipelines_dir = resolve_pipelines_dir(root, config)
        return audit_coverage(root, pipelines, pipelines_dir)

    # mode == "drift"
    return audit_drift(root, pipelines)


# ---------------------------------------------------------------------------
# Public API — discover candidates
# ---------------------------------------------------------------------------


def candidates(root: Path | str, config: GovernanceConfig | None = None) -> CandidateResult:
    """Discover contract-candidate directories in the repository.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.

    Returns:
        CandidateResult with suggested contract candidates.
    """
    root = Path(root)
    pipelines, _ = _load_pipelines(root, config)
    return discover_candidates(root, pipelines)


# ---------------------------------------------------------------------------
# Public API — authority validation
# ---------------------------------------------------------------------------


def authority_verify(root: Path | str, config: GovernanceConfig | None = None) -> AuthorityResult:
    """Validate authority and source-of-truth configuration.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.

    Returns:
        AuthorityResult with authority issues.
    """
    root = Path(root)
    pipelines, _ = _load_pipelines(root, config)
    return verify_authority(root, pipelines)


# ---------------------------------------------------------------------------
# Public API — skills commands
# ---------------------------------------------------------------------------


def skills_index(root: Path | str) -> SkillsResult:
    """Index all skill definitions in the repository.

    Args:
        root: Repo root directory.

    Returns:
        SkillsResult with indexed skill entries.
    """
    return index_skills(Path(root))


def skills_verify(root: Path | str) -> SkillsResult:
    """Index and validate skill definitions in the repository.

    Args:
        root: Repo root directory.

    Returns:
        SkillsResult with validation findings.
    """
    return verify_skills(Path(root))


# ---------------------------------------------------------------------------
# Public API — score command (v0.4 intelligence layer)
# ---------------------------------------------------------------------------


def score(
    root: Path | str,
    config: GovernanceConfig | None = None,
    compare_path: Path | None = None,
) -> ScoreResult:
    """Compute an explainable governance score for the repository.

    Runs all governance checks, scores them by category, prioritizes findings,
    derives cross-signal insights, and optionally computes deltas vs. a
    previous score report.

    Scoring formula (fully transparent):
        Per category: start=100, error=-25 each, warning=-10 each,
        info=not scored, floor=0.
        Overall = mean of all category scores (rounded).

    Categories:
        integrity  — parse errors, schema, integrity, graph, portability
        readiness  — audit readiness findings
        coverage   — audit coverage findings
        drift      — audit drift findings
        authority  — authority validation issues

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.
        compare_path: Optional path to a previous score JSON report for delta.

    Returns:
        ScoreResult with score, prioritized findings, insights, and optional delta.
    """
    root = Path(root)
    if config is None:
        config = load_config(root)

    # ------------------------------------------------------------------
    # Collect findings per category (single pipeline load pass)
    # ------------------------------------------------------------------
    pipelines, parse_errors = _load_pipelines(root, config)

    # integrity: parse + schema + integrity + graph + portability
    schema_issues = validate_pipelines(pipelines)
    integrity_issues = validate_integrity(pipelines)
    graph, graph_issues = build_graph(pipelines)
    cycle_issues = detect_cycles(graph)
    port_issues = scan_pipelines(pipelines)
    integrity_findings = parse_errors + schema_issues + integrity_issues + graph_issues + cycle_issues + port_issues

    # readiness
    readiness_result = audit_readiness(root, pipelines)
    readiness_findings = [
        f for f in readiness_result.findings if f.code != "AUDIT_NO_PIPELINES"
    ]

    # coverage
    pipelines_dir = resolve_pipelines_dir(root, config)
    coverage_result = audit_coverage(root, pipelines, pipelines_dir)
    coverage_findings = [
        f for f in coverage_result.findings if f.code != "AUDIT_NO_SURFACES_FOUND"
    ]

    # drift
    drift_result = audit_drift(root, pipelines)
    drift_findings = [
        f for f in drift_result.findings if f.code != "AUDIT_NO_DRIFT"
    ]

    # authority
    auth_result = verify_authority(root, pipelines)
    authority_findings = list(auth_result.issues)

    # ------------------------------------------------------------------
    # Score each category
    # ------------------------------------------------------------------
    categories = [
        score_category("integrity", integrity_findings),
        score_category("readiness", readiness_findings),
        score_category("coverage", coverage_findings),
        score_category("drift", drift_findings),
        score_category("authority", authority_findings),
    ]

    total = overall_score(categories)

    # ------------------------------------------------------------------
    # Prioritize all findings (combined)
    # ------------------------------------------------------------------
    all_findings = (
        integrity_findings
        + readiness_findings
        + coverage_findings
        + drift_findings
        + authority_findings
    )
    prioritized = sort_by_priority(all_findings)
    prioritized_findings = [
        PrioritizedFinding.from_issue(priority.value, issue)
        for priority, issue in prioritized
    ]

    # ------------------------------------------------------------------
    # Cross-signal insights
    # ------------------------------------------------------------------
    candidate_result = discover_candidates(root, pipelines)
    insights = derive_insights(all_findings, candidate_count=candidate_result.candidate_count)

    # ------------------------------------------------------------------
    # Delta comparison (optional)
    # ------------------------------------------------------------------
    deltas = []
    if compare_path is not None:
        deltas = compute_deltas(total, categories, compare_path)

    return ScoreResult(
        root=root,
        overall_score=total,
        grade=grade(total),
        categories=categories,
        prioritized_findings=prioritized_findings,
        derived_insights=insights,
        delta=deltas,
        formula_explanation=FORMULA_EXPLANATION,
    )


# ---------------------------------------------------------------------------
# Public API — profile commands (v0.5)
# ---------------------------------------------------------------------------


def profile_list() -> list[ProfileDefinition]:
    """Return all registered governance profiles.

    Returns:
        List of ProfileDefinition objects in registration order.
    """
    return list_profiles()


def profile_show(profile_id: str) -> ProfileDefinition | None:
    """Return the ProfileDefinition for *profile_id*, or None if unknown.

    Args:
        profile_id: Profile identifier (e.g. "generic", "codex").

    Returns:
        ProfileDefinition or None if not found.
    """
    from governance_os.profiles.registry import PROFILES

    return PROFILES.get(profile_id)


def profile_validate(
    root: Path | str,
    config: GovernanceConfig | None = None,
) -> tuple[ProfileDefinition, list[str]]:
    """Check whether the repo satisfies the expected surfaces for its configured profile.

    Args:
        root: Repo root directory.
        config: Optional pre-loaded config.

    Returns:
        (profile, missing_surfaces) where missing_surfaces is a list of
        relative paths that the profile expects but do not exist.
        Empty missing_surfaces means the repo is profile-conformant.
    """
    root = Path(root)
    if config is None:
        config = load_config(root)

    profile = resolve_profile(config.profile)
    missing = validate_profile_surfaces(root, profile)
    return profile, missing
