"""Typed configuration model for governance-os."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from governance_os.config.defaults import CONTRACTS_GLOB, PIPELINES_DIR


class GovernanceConfig(BaseSettings):
    """Runtime configuration for governance-os."""

    model_config = SettingsConfigDict(extra="ignore")

    pipelines_dir: str = PIPELINES_DIR
    contracts_glob: str = CONTRACTS_GLOB

    @field_validator("pipelines_dir", "contracts_glob")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v
