"""Typed configuration model for governance-os."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from governance_os.config.defaults import CONTRACTS_GLOB, PIPELINES_DIR


class GovernanceConfig(BaseSettings):
    """Runtime configuration for governance-os.

    All new fields introduced in v0.5 have backward-compatible defaults.
    Existing governance.yaml files without the new fields continue to work.
    """

    model_config = SettingsConfigDict(extra="ignore")

    pipelines_dir: str = PIPELINES_DIR
    contracts_glob: str = CONTRACTS_GLOB

    # v0.5 — profile and plugin configuration
    profile: str = "generic"
    enabled_plugins: list[str] = []
    disabled_plugins: list[str] = []

    @field_validator("pipelines_dir", "contracts_glob")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v
