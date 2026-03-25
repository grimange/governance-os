"""Doctrine plugin for governance-os.

Wraps the existing doctrine validation as an internal plugin.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.models.issue import Issue
from governance_os.models.pipeline import Pipeline
from governance_os.plugins.base import Plugin


class DoctrinePlugin(Plugin):
    """Validates governance doctrine files in governance/doctrine/."""

    plugin_id = "doctrine"
    name = "Doctrine Validation"
    description = "Validates that governance doctrine files exist and are non-empty."

    def run_checks(self, root: Path, pipelines: list[Pipeline]) -> list[Issue]:
        from governance_os.scaffolding.init import validate_doctrine

        issues = validate_doctrine(root)
        return [
            i.model_copy(update={"source": self.plugin_id}) for i in issues
        ]
