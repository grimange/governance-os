"""Scaffold logic for governance-os repo initialization."""

from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_GOVERNANCE_YAML = """\
# governance-os configuration
pipelines_dir: pipelines
contracts_glob: "**/*.md"
"""

_EXAMPLE_CONTRACT = """\
# 001 — Example pipeline

Stage: example

Purpose:
Describe what this pipeline does.

Depends on:

* none

Outputs:

* example artifact

Success criteria:

* criteria met
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
        root / "pipelines",
        root / "docs",
    ]
    for d in directories:
        try:
            d.mkdir(parents=True)
            result.created_dirs.append(d)
        except FileExistsError:
            pass

    files: dict[Path, str] = {
        root / "governance.yaml": _DEFAULT_GOVERNANCE_YAML,
        root / "pipelines" / "001-example.md": _EXAMPLE_CONTRACT,
    }
    for path, content in files.items():
        try:
            path.open("x", encoding="utf-8").write(content)
            result.created_files.append(path)
        except FileExistsError:
            result.skipped_files.append(path)

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
