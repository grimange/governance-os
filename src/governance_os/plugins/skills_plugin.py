"""Skills plugin for governance-os.

Wraps the existing skills validation as an internal plugin.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.models.issue import Issue
from governance_os.models.pipeline import Pipeline
from governance_os.plugins.base import Plugin


class SkillsPlugin(Plugin):
    """Validates skill definitions in the governance/skills/ directory."""

    plugin_id = "skills"
    name = "Skills Validation"
    description = "Validates skill definitions: detects empty files and duplicate IDs."

    def run_checks(self, root: Path, pipelines: list[Pipeline]) -> list[Issue]:
        from governance_os.skills.core import verify_skills

        result = verify_skills(root)
        return [
            i.model_copy(update={"source": self.plugin_id}) for i in result.issues
        ]
