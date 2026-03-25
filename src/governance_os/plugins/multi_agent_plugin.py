"""Multi-agent plugin for governance-os.

Validates multi-agent Codex setup: role definitions, role contracts,
workflow contract, and artifact directories.

This plugin is not active by default. Enable it in governance.yaml:

    enabled_plugins:
      - multi_agent

Repos initialised with `govos init --profile codex --template multi-agent`
have this plugin enabled automatically.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.models.issue import Issue
from governance_os.models.pipeline import Pipeline
from governance_os.plugins.base import Plugin


class MultiAgentPlugin(Plugin):
    """Validates multi-agent governance structure for the Codex profile."""

    plugin_id = "multi_agent"
    name = "Multi-Agent Validation"
    description = "Checks role definitions, role contracts, workflow contract, and artifact dirs."

    def run_checks(self, root: Path, pipelines: list[Pipeline]) -> list[Issue]:
        from governance_os.audit.core import audit_multi_agent

        result = audit_multi_agent(root)
        return [
            i.model_copy(update={"source": self.plugin_id}) for i in result.findings
        ]
