"""governance-os CLI — thin command layer, all logic lives in modules."""

from pathlib import Path
from typing import Optional

import typer

import governance_os.api as api
from governance_os.reporting.console import (
    format_portability,
    format_scan,
    format_status,
    format_verify,
)
from governance_os.reporting.json_report import (
    portability_to_json,
    scan_to_json,
    status_to_json,
    to_json_str,
    verify_to_json,
)
from governance_os.scaffolding.init import format_result, init_repo

app = typer.Typer(
    name="govos",
    help="governance-os: pipeline contract management runtime.",
    no_args_is_help=True,
)

portability_app = typer.Typer(help="Portability analysis commands.")
app.add_typer(portability_app, name="portability")


def _resolve_root(path: str) -> Path:
    return Path(path).resolve()


@app.command()
def init(
    path: str = typer.Argument(".", help="Directory to initialize as a governance repo."),
) -> None:
    """Initialize a governance-os repo with default structure."""
    result = init_repo(_resolve_root(path))
    typer.echo(format_result(result))


@app.command()
def scan(
    path: str = typer.Argument(".", help="Root path to scan for pipeline contracts."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Discover and parse pipeline contracts."""
    root = _resolve_root(path)
    result = api.scan(root)

    if json_output:
        typer.echo(to_json_str(scan_to_json(result)))
        return
    typer.echo(format_scan(result))


@app.command()
def verify(
    path: str = typer.Argument(".", help="Root path to validate pipeline contracts."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Validate pipeline contracts and dependency graph."""
    root = _resolve_root(path)
    result = api.verify(root)

    if json_output:
        typer.echo(to_json_str(verify_to_json(result)))
        raise typer.Exit(0 if result.passed else 1)
    typer.echo(format_verify(result))
    raise typer.Exit(0 if result.passed else 1)


@app.command()
def status(
    path: str = typer.Argument(".", help="Root path to report pipeline status."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Report the status of all pipeline contracts."""
    root = _resolve_root(path)
    result = api.status(root)

    if json_output:
        typer.echo(to_json_str(status_to_json(result)))
        return
    typer.echo(format_status(result))


@portability_app.command("scan")
def portability_scan(
    path: str = typer.Argument(".", help="Root path to scan for portability issues."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Scan pipeline contracts for portability issues."""
    root = _resolve_root(path)
    result = api.portability(root)

    if json_output:
        typer.echo(to_json_str(portability_to_json(result)))
        raise typer.Exit(0 if result.passed else 1)
    typer.echo(format_portability(result))
    raise typer.Exit(0 if result.passed else 1)


if __name__ == "__main__":
    app()
