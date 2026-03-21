"""Pipeline contract discovery for governance-os.

Scans a directory tree for markdown files that match the configured
contracts_glob pattern and returns their paths sorted for stable ordering.
"""

from dataclasses import dataclass, field
from pathlib import Path

from governance_os.config import GovernanceConfig, load_config, resolve_pipelines_dir


@dataclass
class DiscoveryResult:
    """Result of a contract discovery scan."""

    pipelines_dir: Path
    contracts: list[Path] = field(default_factory=list)
    missing_dir: bool = False


def discover(root: Path, config: GovernanceConfig | None = None) -> DiscoveryResult:
    """Discover pipeline contract files under *root*.

    Args:
        root: Repo root directory.
        config: Pre-loaded config. If None, loaded from *root*.

    Returns:
        DiscoveryResult with found contract paths sorted by name.
    """
    if config is None:
        config = load_config(root)

    pipelines_dir = resolve_pipelines_dir(root, config)

    if not pipelines_dir.exists():
        return DiscoveryResult(pipelines_dir=pipelines_dir, missing_dir=True)

    contracts = sorted(
        pipelines_dir.glob(config.contracts_glob),
        key=lambda p: p.name,
    )

    return DiscoveryResult(pipelines_dir=pipelines_dir, contracts=contracts)


def format_result(result: DiscoveryResult, root: Path) -> str:
    """Return a human-readable summary of a DiscoveryResult.

    Args:
        result: The result to format.
        root: Repo root used to make paths relative for display.

    Returns:
        Multi-line string suitable for CLI output.
    """
    if result.missing_dir:
        return (
            f"Pipelines directory not found: {result.pipelines_dir}\n"
            "Run `govos init` to create the default structure."
        )

    if not result.contracts:
        return f"No contracts found in: {result.pipelines_dir}"

    lines = [f"Found {len(result.contracts)} contract(s) in {result.pipelines_dir.relative_to(root)}:"]
    for contract in result.contracts:
        lines.append(f"  {contract.relative_to(root)}")
    return "\n".join(lines)
