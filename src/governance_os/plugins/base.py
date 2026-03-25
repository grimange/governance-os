"""Base class for governance-os internal plugins.

Plugins are simple objects with a plugin_id, name, description,
and a run_checks() method. No complex lifecycle. No external loading.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from governance_os.models.issue import Issue
from governance_os.models.pipeline import Pipeline


class Plugin(ABC):
    """Base class for all internal governance-os plugins.

    Subclasses must set class attributes:
        plugin_id  — stable machine-readable identifier
        name       — human-readable display name
        description — one-line description of what this plugin checks

    Subclasses must implement:
        run_checks() — returns a list of Issue objects
    """

    plugin_id: str = ""
    name: str = ""
    description: str = ""

    @abstractmethod
    def run_checks(self, root: Path, pipelines: list[Pipeline]) -> list[Issue]:
        """Run this plugin's checks against the repository.

        Args:
            root: Repo root directory.
            pipelines: Parsed pipeline contracts (may be empty).

        Returns:
            List of Issue objects. Empty list means no issues found.
            Issues should include source=self.plugin_id.
        """
        ...  # pragma: no cover
