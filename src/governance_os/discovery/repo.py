"""Repo root resolution for governance-os discovery."""

from pathlib import Path

from governance_os.config import GovernanceConfig, load_config, resolve_pipelines_dir


def get_pipelines_dir(root: Path, config: GovernanceConfig | None = None) -> Path:
    """Return the absolute path to the pipelines directory for *root*.

    Args:
        root: Repo root directory.
        config: Pre-loaded config. If None, loaded from *root*.

    Returns:
        Absolute Path to the configured pipelines directory.
    """
    if config is None:
        config = load_config(root)
    return resolve_pipelines_dir(root, config)
