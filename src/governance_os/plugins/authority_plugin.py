"""Authority plugin for governance-os.

Wraps the existing authority validation module as an internal plugin.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.models.issue import Issue
from governance_os.models.pipeline import Pipeline
from governance_os.plugins.base import Plugin


class AuthorityPlugin(Plugin):
    """Validates source-of-truth configuration (governance.yaml, contract locations)."""

    plugin_id = "authority"
    name = "Authority Validation"
    description = "Validates authority configuration and source-of-truth file locations."

    def run_checks(self, root: Path, pipelines: list[Pipeline]) -> list[Issue]:
        from governance_os.authority.core import verify_authority

        result = verify_authority(root, pipelines)
        return [
            i.model_copy(update={"source": self.plugin_id}) for i in result.issues
        ]
