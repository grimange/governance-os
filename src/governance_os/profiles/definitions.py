"""Profile definition model for governance-os.

Profiles are data definitions — they carry conventions and defaults.
They do not contain custom execution logic.

All profiles are first-party and statically defined here.
There is no remote profile registry or dynamic loading.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProfileDefinition:
    """Definition of a governance-os profile.

    Attributes:
        id: Machine-readable profile identifier.
        name: Human-readable display name.
        description: Concise description of the profile's purpose and conventions.
        default_plugins: Plugin IDs active by default for this profile.
            May be extended or overridden by repo config.
        expected_surfaces: Repo paths that should exist for a profile-conformant repo.
            Used by `govos profile validate` to detect missing surfaces.
        optional_surfaces: Repo paths that may exist for this profile (advisory only).
        scaffold_groups: Scaffold asset groups applied during `govos init`.
    """

    id: str
    name: str
    description: str
    default_plugins: tuple[str, ...] = field(default_factory=tuple)
    expected_surfaces: tuple[str, ...] = field(default_factory=tuple)
    optional_surfaces: tuple[str, ...] = field(default_factory=tuple)
    scaffold_groups: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Built-in profile definitions
# ---------------------------------------------------------------------------

GENERIC = ProfileDefinition(
    id="generic",
    name="Generic",
    description=(
        "Vendor-neutral governance structure. "
        "No agent-specific assumptions. "
        "Suitable for any team or toolchain."
    ),
    default_plugins=(),
    expected_surfaces=(
        "governance/pipelines",
        "artifacts",
        "governance.yaml",
    ),
    optional_surfaces=(
        "governance/skills",
        "governance/doctrine",
        "docs/governance",
    ),
    scaffold_groups=("common",),
)

CODEX = ProfileDefinition(
    id="codex",
    name="Codex",
    description=(
        "Codex-oriented governance. "
        "Adds session contracts (governance/sessions/) and Codex instruction checks. "
        "Expects AGENTS.md at the repo root."
    ),
    default_plugins=("codex_instructions",),
    expected_surfaces=(
        "governance/pipelines",
        "artifacts",
        "governance.yaml",
        "AGENTS.md",
    ),
    optional_surfaces=(
        "governance/sessions",
        "governance/skills",
        "governance/doctrine",
        "docs/governance",
    ),
    scaffold_groups=("common", "codex"),
)
