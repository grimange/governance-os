"""governance-os configuration package."""

from governance_os.config.loader import load_config, resolve_pipelines_dir
from governance_os.config.models import GovernanceConfig

__all__ = ["GovernanceConfig", "load_config", "resolve_pipelines_dir"]
