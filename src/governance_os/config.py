"""Configuration loading for governance-os.

Reads governance.yaml from the repo root. Falls back to defaults
if the file is absent so the package works without any config file.
"""

from pathlib import Path

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GovernanceConfig(BaseSettings):
    """Runtime configuration for governance-os."""

    model_config = SettingsConfigDict(extra="ignore")

    # Directory (relative to repo root) containing pipeline contracts.
    pipelines_dir: str = "pipelines"

    # Glob pattern used when scanning pipelines_dir for contract files.
    contracts_glob: str = "**/*.md"

    @field_validator("pipelines_dir", "contracts_glob")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


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
