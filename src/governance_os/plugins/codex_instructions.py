"""Codex instructions plugin for governance-os.

Checks for Codex-specific governance artifacts (AGENTS.md).
This plugin is active by default for the `codex` profile only.
It is never activated for the `generic` profile unless explicitly enabled.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline
from governance_os.plugins.base import Plugin

# Minimum meaningful content: at least this many non-empty lines
_MIN_CONTENT_LINES = 3


class CodexInstructionsPlugin(Plugin):
    """Checks for Codex-specific governance files.

    Checks:
      CODEX_MISSING_AGENTS_MD  — AGENTS.md not found at repo root
      CODEX_EMPTY_AGENTS_MD    — AGENTS.md is empty
    """

    plugin_id = "codex_instructions"
    name = "Codex Instructions"
    description = "Checks for AGENTS.md and Codex-specific governance artifacts."

    def run_checks(self, root: Path, pipelines: list[Pipeline]) -> list[Issue]:
        issues: list[Issue] = []
        agents_md = root / "AGENTS.md"

        if not agents_md.exists():
            issues.append(
                Issue(
                    code="CODEX_MISSING_AGENTS_MD",
                    severity=Severity.WARNING,
                    message=(
                        "AGENTS.md not found at repo root. "
                        "Codex profile repos should include AGENTS.md with governance instructions."
                    ),
                    path=root,
                    suggestion=(
                        "Create AGENTS.md at the repo root. "
                        "Run `govos init --profile codex` to scaffold a template."
                    ),
                    source=self.plugin_id,
                )
            )
            return issues

        content = agents_md.read_text(encoding="utf-8").strip()
        if not content:
            issues.append(
                Issue(
                    code="CODEX_EMPTY_AGENTS_MD",
                    severity=Severity.WARNING,
                    message="AGENTS.md exists but is empty.",
                    path=agents_md,
                    suggestion="Add governance instructions for Codex to AGENTS.md.",
                    source=self.plugin_id,
                )
            )
        elif len([line for line in content.splitlines() if line.strip()]) < _MIN_CONTENT_LINES:
            issues.append(
                Issue(
                    code="CODEX_AGENTS_MD_SPARSE",
                    severity=Severity.INFO,
                    message=(
                        f"AGENTS.md appears sparse (fewer than {_MIN_CONTENT_LINES} non-empty lines). "
                        "Consider adding governance rules and quick reference commands."
                    ),
                    path=agents_md,
                    source=self.plugin_id,
                )
            )

        return issues
