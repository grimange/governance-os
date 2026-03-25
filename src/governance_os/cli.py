"""governance-os CLI — thin command layer, all logic lives in modules."""

from pathlib import Path

import typer

import governance_os.api as api
from governance_os.reporting.console import (
    format_audit,
    format_authority,
    format_candidates,
    format_portability,
    format_preflight,
    format_registry,
    format_scan,
    format_skills,
    format_status,
    format_verify,
)
from governance_os.reporting.json_report import (
    audit_to_json,
    authority_to_json,
    candidates_to_json,
    portability_to_json,
    preflight_to_json,
    registry_to_json,
    scan_to_json,
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
    skills_report,
    status_report,
    verify_report,
    write_report,
)
from governance_os.scaffolding.init import format_result, init_repo, validate_doctrine

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
    level: str = typer.Option("standard", "--level", help="Governance maturity level: minimal, standard, governed."),
    profile: str = typer.Option("generic", "--profile", help="Optional profile: generic, codex."),
    with_doctrine: bool = typer.Option(False, "--with-doctrine", help="Scaffold an optional doctrine file."),
) -> None:
    """Initialize a governance-os repo with default structure."""
    result = init_repo(_resolve_root(path), level=level, profile=profile, with_doctrine=with_doctrine)
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
        return
    output = format_scan(result)
    typer.echo(output)
    _maybe_write(scan_report(result), out)


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
        return
    output = format_status(result)
    typer.echo(output)
    _maybe_write(status_report(result), out)


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
    result = api.preflight(root, include_authority=authority, include_portability=not no_portability)

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
        return
    output = format_registry(result)
    typer.echo(output)
    _maybe_write(registry_report(result), out)


@registry_app.command("verify")
def registry_verify(
    path: str = typer.Argument(".", help="Root path to verify registry for."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    out: Path | None = typer.Option(None, "--out", help="Write report to this file path."),
    snapshot: Path | None = typer.Option(None, "--snapshot", help="Path to existing registry JSON snapshot."),
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
        return
    typer.echo(format_audit(result))
    _maybe_write(audit_report(result), out)


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
        return
    typer.echo(format_audit(result))
    _maybe_write(audit_report(result), out)


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
        return
    typer.echo(format_audit(result))
    _maybe_write(audit_report(result), out)


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
        return
    typer.echo(format_candidates(result))
    _maybe_write(candidates_report(result), out)


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
        return
    typer.echo(format_skills(result))
    _maybe_write(skills_report(result), out)


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
    """Validate that a governance doctrine file exists and is complete."""
    root = _resolve_root(path)
    issues = validate_doctrine(root)

    if not issues:
        typer.echo("OK — doctrine file is present and non-empty.")
        return

    typer.echo(f"FAIL — {len(issues)} doctrine issue(s):")
    for issue in issues:
        typer.echo(f"  {issue}")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
