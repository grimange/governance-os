"""governance-os CLI — thin command layer, all logic lives in modules."""

from pathlib import Path

import typer

import governance_os.api as api
from governance_os.reporting.console import (
    format_audit,
    format_authority,
    format_candidates,
    format_lifecycle,
    format_lifecycle_record,
    format_portability,
    format_preflight,
    format_registry,
    format_scan,
    format_score,
    format_skills,
    format_status,
    format_verify,
)
from governance_os.reporting.json_report import (
    audit_to_json,
    authority_to_json,
    candidates_to_json,
    lifecycle_record_to_json,
    lifecycle_to_json,
    portability_to_json,
    preflight_to_json,
    registry_to_json,
    scan_to_json,
    score_to_json,
    skills_to_json,
    status_to_json,
    to_json_str,
    verify_to_json,
)
from governance_os.reporting.markdown import (
    audit_report,
    authority_report,
    candidates_report,
    portability_report,
    preflight_report,
    registry_report,
    scan_report,
    score_report,
    skills_report,
    status_report,
    verify_report,
    write_report,
)
from governance_os.scaffolding.init import (
    ConflictPolicy,
    execute_plan,
    format_plan,
    format_result,
    init_repo,
    plan_scaffold,
    validate_doctrine,
    validate_scaffold,
)

app = typer.Typer(
    name="govos",
    help="governance-os: pipeline contract management runtime.",
    no_args_is_help=True,
)

portability_app = typer.Typer(help="Portability analysis commands.")
app.add_typer(portability_app, name="portability")

registry_app = typer.Typer(help="Pipeline registry commands.")
app.add_typer(registry_app, name="registry")

audit_app = typer.Typer(help="Governance audit commands.")
app.add_typer(audit_app, name="audit")

discover_app = typer.Typer(help="Contract discovery commands.")
app.add_typer(discover_app, name="discover")

authority_app = typer.Typer(help="Authority and source-of-truth commands.")
app.add_typer(authority_app, name="authority")

skills_app = typer.Typer(help="Skills index and validation commands.")
app.add_typer(skills_app, name="skills")

doctrine_app = typer.Typer(help="Doctrine scaffolding and validation commands.")
app.add_typer(doctrine_app, name="doctrine")

profile_app = typer.Typer(help="Profile inspection and validation commands.")
app.add_typer(profile_app, name="profile")

pipeline_app = typer.Typer(help="Pipeline lifecycle commands.")
app.add_typer(pipeline_app, name="pipeline")

plugin_app = typer.Typer(help="Plugin inspection commands.")
app.add_typer(plugin_app, name="plugin")


def _resolve_root(path: str) -> Path:
    return Path(path).resolve()


def _maybe_write(content: str, out: Path | None) -> None:
    """Write *content* to *out* if provided."""
    if out is not None:
        write_report(content, out)
        typer.echo(f"Report written to: {out}")


def _maybe_write_json(data: dict, out: Path | None) -> None:
    """Write JSON *data* to *out* if provided."""
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(to_json_str(data), encoding="utf-8")
        typer.echo(f"JSON written to: {out}")


# ---------------------------------------------------------------------------
# Core commands
# ---------------------------------------------------------------------------


@app.command()
def init(
    path: str = typer.Argument(".", help="Directory to initialize as a governance repo."),
    template: str | None = typer.Option(
        None,
        "--template",
        help="Scaffold template: minimal or governed. Takes precedence over --level.",
    ),
    level: str = typer.Option(
        "standard",
        "--level",
        help="Governance maturity level: minimal, standard, governed. Legacy; prefer --template.",
    ),
    profile: str = typer.Option("generic", "--profile", help="Profile: generic or codex."),
    with_doctrine: bool = typer.Option(
        False, "--with-doctrine", help="Scaffold an optional doctrine file."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be created without writing any files."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing files instead of skipping them."
    ),
) -> None:
    """Initialize a governance-os repo with default structure.

    Use --profile to select the environment convention and --template to select
    the scaffold surface area. Use --dry-run to preview changes without writing.
    Use --force to overwrite existing files.

    Examples:
      govos init --profile generic --template minimal
      govos init --profile codex --template minimal
      govos init --profile codex --template governed
      govos init --dry-run
      govos init --force
    """
    root = _resolve_root(path)
    # Resolve effective template: explicit --template takes precedence over --level
    effective_template = template if template is not None else level
    try:
        plan = plan_scaffold(root, profile=profile, template=effective_template, with_doctrine=with_doctrine)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2)  # usage/input error

    if dry_run:
        typer.echo(format_plan(plan, check_existing=True))
        raise typer.Exit(0)

    conflict = ConflictPolicy.OVERWRITE if force else ConflictPolicy.SKIP
    try:
        result = execute_plan(plan, conflict=conflict)
    except FileExistsError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    issues = validate_scaffold(root, plan)
    if issues:
        from governance_os.models.issue import Severity
        for issue in issues:
            severity_label = "WARN" if issue.severity == Severity.WARNING else issue.severity.upper()
            typer.echo(f"  [{severity_label}] {issue.message}", err=True)

    typer.echo(format_result(result))


@app.command()
def scan(
    path: str = typer.Argument(".", help="Root path to scan for pipeline contracts."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Discover and parse pipeline contracts."""
    root = _resolve_root(path)
    result = api.scan(root)

    if json_output:
        data = scan_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    output = format_scan(result)
    typer.echo(output)
    _maybe_write(scan_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


@app.command()
def verify(
    path: str = typer.Argument(".", help="Root path to validate pipeline contracts."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Validate pipeline contracts and dependency graph."""
    root = _resolve_root(path)
    result = api.verify(root)

    if json_output:
        data = verify_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    output = format_verify(result)
    typer.echo(output)
    _maybe_write(verify_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


@app.command()
def status(
    path: str = typer.Argument(".", help="Root path to report pipeline status."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Report the status of all pipeline contracts."""
    root = _resolve_root(path)
    result = api.status(root)

    if json_output:
        data = status_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0)
    output = format_status(result)
    typer.echo(output)
    _maybe_write(status_report(result), out)
    raise typer.Exit(0)


@app.command()
def preflight(
    path: str = typer.Argument(".", help="Root path for preflight check."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
    authority: bool = typer.Option(False, "--authority", help="Include authority validation."),
    no_portability: bool = typer.Option(False, "--no-portability", help="Skip portability checks."),
) -> None:
    """Run a fail-closed preflight governance readiness check."""
    root = _resolve_root(path)
    result = api.preflight(
        root, include_authority=authority, include_portability=not no_portability
    )

    if json_output:
        data = preflight_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    output = format_preflight(result)
    typer.echo(output)
    _maybe_write(preflight_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


# ---------------------------------------------------------------------------
# Score command (v0.4 intelligence layer)
# ---------------------------------------------------------------------------


@app.command()
def score(
    path: str = typer.Argument(".", help="Root path to score."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
    compare: Path | None = typer.Option(
        None, "--compare", help="Path to a previous score JSON report for delta comparison."
    ),
    explain: bool = typer.Option(
        False, "--explain", help="Include scoring formula explanation in output."
    ),
) -> None:
    """Compute an explainable governance score for the repository.

    Scores five categories: integrity, readiness, coverage, drift, authority.
    Each category starts at 100; errors deduct 25 pts, warnings deduct 10 pts.
    Overall score is the mean of all category scores.
    """
    root = _resolve_root(path)
    result = api.score(root, compare_path=compare)

    if json_output:
        data = score_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0)
    typer.echo(format_score(result, explain=explain))
    _maybe_write(score_report(result, explain=explain), out)
    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# Portability commands
# ---------------------------------------------------------------------------


@portability_app.command("scan")
def portability_scan(
    path: str = typer.Argument(".", help="Root path to scan for portability issues."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Scan pipeline contracts for portability issues."""
    root = _resolve_root(path)
    result = api.portability(root)

    if json_output:
        data = portability_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    output = format_portability(result)
    typer.echo(output)
    _maybe_write(portability_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


# ---------------------------------------------------------------------------
# Registry commands
# ---------------------------------------------------------------------------


@registry_app.command("build")
def registry_build(
    path: str = typer.Argument(".", help="Root path to build registry from."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write registry output to this file path."),
) -> None:
    """Build a registry snapshot from all discovered pipeline contracts."""
    root = _resolve_root(path)
    result = api.registry_build(root)

    if json_output:
        data = registry_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    output = format_registry(result)
    typer.echo(output)
    _maybe_write(registry_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


@registry_app.command("verify")
def registry_verify(
    path: str = typer.Argument(".", help="Root path to verify registry for."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
    snapshot: Path | None = typer.Option(
        None, "--snapshot", help="Path to existing registry JSON snapshot."
    ),
) -> None:
    """Verify registry integrity, optionally reconciling against a snapshot."""
    root = _resolve_root(path)
    result = api.registry_verify(root, registry_path=snapshot)

    if json_output:
        data = registry_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    output = format_registry(result)
    typer.echo(output)
    _maybe_write(registry_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


# ---------------------------------------------------------------------------
# Audit commands
# ---------------------------------------------------------------------------


@audit_app.command("readiness")
def audit_readiness(
    path: str = typer.Argument(".", help="Root path to audit."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Audit governance readiness: find contracts missing required sections."""
    root = _resolve_root(path)
    result = api.audit(root, mode="readiness")

    if json_output:
        data = audit_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    typer.echo(format_audit(result))
    _maybe_write(audit_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


@audit_app.command("coverage")
def audit_coverage(
    path: str = typer.Argument(".", help="Root path to audit."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Audit governance coverage: find uncontracted pipeline-like directories."""
    root = _resolve_root(path)
    result = api.audit(root, mode="coverage")

    if json_output:
        data = audit_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    typer.echo(format_audit(result))
    _maybe_write(audit_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


@audit_app.command("drift")
def audit_drift(
    path: str = typer.Argument(".", help="Root path to audit."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Audit output drift: find declared outputs that do not exist on disk."""
    root = _resolve_root(path)
    result = api.audit(root, mode="drift")

    if json_output:
        data = audit_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    typer.echo(format_audit(result))
    _maybe_write(audit_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


@audit_app.command("multi-agent")
def audit_multi_agent(
    path: str = typer.Argument(".", help="Root path to audit."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Audit multi-agent Codex setup: check roles, contracts, workflow, and artifact dirs."""
    root = _resolve_root(path)
    result = api.audit(root, mode="multi-agent")

    if json_output:
        data = audit_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    typer.echo(format_audit(result))
    _maybe_write(audit_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


# ---------------------------------------------------------------------------
# Discover commands
# ---------------------------------------------------------------------------


@discover_app.command("candidates")
def discover_candidates(
    path: str = typer.Argument(".", help="Root path to scan for candidates."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Discover pipeline-like directories that lack governance contracts."""
    root = _resolve_root(path)
    result = api.candidates(root)

    if json_output:
        data = candidates_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0)
    typer.echo(format_candidates(result))
    _maybe_write(candidates_report(result), out)
    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# Authority commands
# ---------------------------------------------------------------------------


@authority_app.command("verify")
def authority_verify(
    path: str = typer.Argument(".", help="Root path to verify authority for."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Validate authority and source-of-truth configuration."""
    root = _resolve_root(path)
    result = api.authority_verify(root)

    if json_output:
        data = authority_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    output = format_authority(result)
    typer.echo(output)
    _maybe_write(authority_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


# ---------------------------------------------------------------------------
# Skills commands
# ---------------------------------------------------------------------------


@skills_app.command("index")
def skills_index(
    path: str = typer.Argument(".", help="Root path to index skills from."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Index all skill definitions in the repository."""
    root = _resolve_root(path)
    result = api.skills_index(root)

    if json_output:
        data = skills_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0)
    typer.echo(format_skills(result))
    _maybe_write(skills_report(result), out)
    raise typer.Exit(0)


@skills_app.command("verify")
def skills_verify(
    path: str = typer.Argument(".", help="Root path to verify skills for."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Index and validate skill definitions in the repository."""
    root = _resolve_root(path)
    result = api.skills_verify(root)

    if json_output:
        data = skills_to_json(result)
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if result.passed else 1)
    output = format_skills(result)
    typer.echo(output)
    _maybe_write(skills_report(result), out)
    raise typer.Exit(0 if result.passed else 1)


# ---------------------------------------------------------------------------
# Doctrine commands
# ---------------------------------------------------------------------------


@doctrine_app.command("validate")
def doctrine_validate(
    path: str = typer.Argument(".", help="Root path to validate doctrine for."),
) -> None:
    """Validate that a governance doctrine pack exists and is complete."""
    from governance_os.models.issue import Severity

    root = _resolve_root(path)
    issues = validate_doctrine(root)

    has_errors = any(i.severity == Severity.ERROR for i in issues)

    if not issues:
        typer.echo("OK — doctrine file is present and non-empty.")
        raise typer.Exit(0)

    status = "FAIL" if has_errors else "OK"
    typer.echo(f"{status} — {len(issues)} doctrine issue(s):")
    for issue in issues:
        typer.echo(f"  [{issue.severity.upper()}] [{issue.code}] {issue.message}")
    raise typer.Exit(1 if has_errors else 0)


# ---------------------------------------------------------------------------
# Profile commands (v0.5)
# ---------------------------------------------------------------------------


@profile_app.command("list")
def profile_list_cmd() -> None:
    """List all available governance profiles."""
    profiles = api.profile_list()
    for p in profiles:
        plugins = ", ".join(p.default_plugins) if p.default_plugins else "none"
        templates = ", ".join(p.supported_templates) if p.supported_templates else "none"
        typer.echo(f"  [{p.id}] {p.name}")
        typer.echo(f"    {p.description}")
        typer.echo(f"    templates: {templates}")
        typer.echo(f"    default plugins: {plugins}")
        typer.echo("")


@profile_app.command("show")
def profile_show_cmd(
    profile_id: str = typer.Argument(..., help="Profile ID to show (e.g. generic, codex)."),
) -> None:
    """Show details of a specific governance profile."""
    profile = api.profile_show(profile_id)
    if profile is None:
        typer.echo(f"Profile not found: {profile_id!r}", err=True)
        raise typer.Exit(2)  # usage/input error

    typer.echo(f"Profile: {profile.id}")
    typer.echo(f"  Name: {profile.name}")
    typer.echo(f"  Description: {profile.description}")
    if profile.supported_templates:
        typer.echo(f"  Supported templates: {', '.join(profile.supported_templates)}")
    if profile.default_plugins:
        typer.echo(f"  Default plugins: {', '.join(profile.default_plugins)}")
    else:
        typer.echo("  Default plugins: none")
    if profile.expected_surfaces:
        typer.echo("  Expected surfaces:")
        for s in profile.expected_surfaces:
            typer.echo(f"    - {s}")
    if profile.optional_surfaces:
        typer.echo("  Optional surfaces:")
        for s in profile.optional_surfaces:
            typer.echo(f"    - {s}")


@profile_app.command("validate")
def profile_validate_cmd(
    path: str = typer.Argument(".", help="Root path to validate against active profile."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
) -> None:
    """Validate that the repo satisfies the expected surfaces for its profile.

    Checks that all paths declared as expected_surfaces in the active profile exist.
    Reads the profile from governance.yaml (or defaults to 'generic').
    """
    root = _resolve_root(path)
    profile, missing = api.profile_validate(root)

    if json_output:
        data = {
            "command": "profile validate",
            "root": str(root),
            "profile": profile.id,
            "passed": len(missing) == 0,
            "missing_surfaces": missing,
        }
        typer.echo(to_json_str(data))
        _maybe_write_json(data, out)
        raise typer.Exit(0 if not missing else 1)

    if not missing:
        typer.echo(f"OK — profile '{profile.id}' is satisfied. All expected surfaces present.")
    else:
        typer.echo(f"INCOMPLETE — profile '{profile.id}' expected surfaces missing:")
        for m in missing:
            typer.echo(f"  - {m}")
    raise typer.Exit(0 if not missing else 1)


# ---------------------------------------------------------------------------
# Pipeline lifecycle commands
# ---------------------------------------------------------------------------


@pipeline_app.command("list")
def pipeline_list_cmd(
    path: str = typer.Argument(".", help="Root path to scan for pipeline contracts."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """List all pipelines with their effective lifecycle states."""
    root = _resolve_root(path)
    result = api.pipeline_lifecycle(root)
    if json_output:
        typer.echo(to_json_str(lifecycle_to_json(result)))
        raise typer.Exit(0)
    typer.echo(format_lifecycle(result))
    raise typer.Exit(0)


@pipeline_app.command("status")
def pipeline_status_cmd(
    pipeline_id: str = typer.Argument(..., help="Pipeline numeric ID or slug."),
    path: str = typer.Option(".", "--root", help="Root path of the governance repo."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Show the lifecycle status for a single pipeline."""
    root = _resolve_root(path)
    record = api.pipeline_lifecycle_status(root, pipeline_id)
    if record is None:
        typer.echo(f"Pipeline '{pipeline_id}' not found.", err=True)
        raise typer.Exit(2)  # usage/input error
    if json_output:
        typer.echo(to_json_str(lifecycle_record_to_json(record)))
        raise typer.Exit(0)
    typer.echo(format_lifecycle_record(record))
    raise typer.Exit(0)


@pipeline_app.command("verify")
def pipeline_verify_cmd(
    pipeline_id: str = typer.Argument(..., help="Pipeline numeric ID or slug."),
    path: str = typer.Option(".", "--root", help="Root path of the governance repo."),
) -> None:
    """Verify lifecycle integrity for a single pipeline.

    Exits 1 if the pipeline has lifecycle drift (declared != effective state).
    Exits 2 if the pipeline ID is not found.
    """
    root = _resolve_root(path)
    record = api.pipeline_lifecycle_status(root, pipeline_id)
    if record is None:
        typer.echo(f"Pipeline '{pipeline_id}' not found.", err=True)
        raise typer.Exit(2)  # usage/input error
    typer.echo(format_lifecycle_record(record))
    if record.drift:
        typer.echo(
            f"\nFAIL — lifecycle drift: declared='{record.declared_state}' "
            f"effective='{record.effective_state}'"
        )
        raise typer.Exit(1)
    typer.echo("\nOK — lifecycle state is consistent.")
    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# Plugin commands
# ---------------------------------------------------------------------------


@plugin_app.command("list")
def plugin_list_cmd() -> None:
    """List all registered governance plugins."""
    plugins = api.plugin_list()
    for p in plugins:
        typer.echo(f"  [{p.plugin_id}] {p.name}")
        typer.echo(f"    {p.description}")
        typer.echo("")
    raise typer.Exit(0)


@plugin_app.command("show")
def plugin_show_cmd(
    plugin_id: str = typer.Argument(..., help="Plugin ID to show (e.g. authority, skills)."),
) -> None:
    """Show details of a specific governance plugin."""
    plugin = api.plugin_show(plugin_id)
    if plugin is None:
        typer.echo(f"Plugin not found: {plugin_id!r}", err=True)
        raise typer.Exit(2)  # usage/input error

    typer.echo(f"Plugin: {plugin.plugin_id}")
    typer.echo(f"  Name: {plugin.name}")
    typer.echo(f"  Description: {plugin.description}")
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
