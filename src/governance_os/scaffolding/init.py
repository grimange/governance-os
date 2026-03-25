"""Scaffold logic for governance-os repo initialization."""

from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path


def _template(name: str) -> str:
    return files("governance_os.templates").joinpath(name).read_text(encoding="utf-8")


_EXAMPLE_PIPELINE = """\
# 001 — Example Pipeline

Stage: establish

Purpose:
Describe what this pipeline does.

Depends on:
- none

Outputs:
- example artifact

Success criteria:
- criteria met

Out of scope:
- nothing yet
"""


@dataclass
class ScaffoldResult:
    """Result of a scaffold operation."""

    root: Path
    created_dirs: list[Path] = field(default_factory=list)
    created_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)


def init_repo(root: Path) -> ScaffoldResult:
    """Initialize a governance-os repo at *root*.

    Creates the standard directory layout and default files.
    Existing files are never overwritten.

    Args:
        root: Target directory (created if it does not exist).

    Returns:
        ScaffoldResult describing what was created or skipped.
    """
    result = ScaffoldResult(root=root)

    directories = [
        root / "governance" / "pipelines",
        root / "docs" / "governance",
        root / "artifacts",
    ]
    for d in directories:
        if not d.exists():
            d.mkdir(parents=True)
            result.created_dirs.append(d)

    files_to_create: dict[Path, str] = {
        root / "governance.yaml": _template("governance.yaml"),
        root / "governance" / "pipelines" / "001--example.md": _EXAMPLE_PIPELINE,
        root / "docs" / "governance" / "README.governance.md": _template(
            "README.governance.md"
        ),
    }
    for path, content in files_to_create.items():
        if path.exists():
            result.skipped_files.append(path)
        else:
            path.write_text(content, encoding="utf-8")
            result.created_files.append(path)

    return result


def format_result(result: ScaffoldResult) -> str:
    """Return a human-readable summary of a ScaffoldResult.

    Args:
        result: The result to format.

    Returns:
        Multi-line string suitable for CLI output.
    """
    lines: list[str] = [f"Initialized governance-os repo at: {result.root}"]

    if result.created_dirs:
        lines.append("\nDirectories created:")
        for d in result.created_dirs:
            lines.append(f"  + {d.relative_to(result.root)}/")

    if result.created_files:
        lines.append("\nFiles created:")
        for f in result.created_files:
            lines.append(f"  + {f.relative_to(result.root)}")

    if result.skipped_files:
        lines.append("\nFiles skipped (already exist):")
        for f in result.skipped_files:
            lines.append(f"  ~ {f.relative_to(result.root)}")

    return "\n".join(lines)
