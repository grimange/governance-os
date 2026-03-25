"""Config loader for governance-os.

Reads governance.yaml from the repo root. Falls back to defaults
if the file is absent so the package works without any config file.
"""

from pathlib import Path

import yaml

from governance_os.config.models import GovernanceConfig


def load_config(root: Path | None = None) -> GovernanceConfig:
    """Load GovernanceConfig from governance.yaml in *root*.

    Args:
        root: Repo root directory. Defaults to the current working directory.

    Returns:
        A populated GovernanceConfig instance.
    """
    root = root or Path.cwd()
    config_path = root / "governance.yaml"

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        raw = {}

    return GovernanceConfig(**raw)


def resolve_pipelines_dir(root: Path, config: GovernanceConfig) -> Path:
    """Return the absolute path to the pipelines directory.

    Args:
        root: Repo root directory.
        config: Loaded GovernanceConfig.

    Returns:
        Absolute Path to the pipelines directory.
    """
    return root / config.pipelines_dir
