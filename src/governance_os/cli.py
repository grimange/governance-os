"""governance-os CLI — thin command layer, all logic lives in modules."""

from pathlib import Path

import typer

import governance_os.discovery as discovery_mod
from governance_os.scaffold import format_result, init_repo

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
) -> None:
    """Discover and parse pipeline contracts."""
    root = _resolve_root(path)
    result = discovery_mod.discover(root)
    typer.echo(discovery_mod.format_result(result, root))


@app.command()
def verify(
    path: str = typer.Argument(".", help="Root path to validate pipeline contracts."),
) -> None:
    """Validate pipeline contracts and dependency graph."""
    typer.echo(f"[govos verify] Not yet implemented. Target: {path}")


@app.command()
def status(
    path: str = typer.Argument(".", help="Root path to report pipeline status."),
) -> None:
    """Report the status of all pipeline contracts."""
    typer.echo(f"[govos status] Not yet implemented. Target: {path}")


@portability_app.command("scan")
def portability_scan(
    path: str = typer.Argument(".", help="Root path to scan for portability issues."),
) -> None:
    """Scan pipeline contracts for portability issues."""
    typer.echo(f"[govos portability scan] Not yet implemented. Target: {path}")


if __name__ == "__main__":
    app()
