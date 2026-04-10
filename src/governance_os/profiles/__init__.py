"""Profile definitions for governance-os.

Profiles define repo-level governance conventions, expected surfaces,
default active plugins, and scaffold behavior.

Available profiles:
  generic   — vendor-neutral, no agent-specific assumptions (default)
  codex     — Codex-oriented, adds session contracts and AGENTS.md checks
"""

from governance_os.profiles.definitions import ProfileDefinition
from governance_os.profiles.registry import (
    PROFILES,
    is_known_profile,
    list_profiles,
    resolve_profile,
    validate_profile_surfaces,
)

__all__ = [
    "ProfileDefinition",
    "PROFILES",
    "is_known_profile",
    "list_profiles",
    "resolve_profile",
    "validate_profile_surfaces",
]
