"""Profile registry and resolution for governance-os.

All profiles are statically registered here. There is no dynamic loading.

Resolution order for the effective profile:
  1. Explicit argument passed to the API function (highest priority).
  2. `profile` field in repo governance.yaml.
  3. Fallback: "generic".
"""

from __future__ import annotations

from pathlib import Path

from governance_os.profiles.definitions import (
    CODEX,
    GENERIC,
    ProfileDefinition,
)

# ---------------------------------------------------------------------------
# Static profile registry
# ---------------------------------------------------------------------------

PROFILES: dict[str, ProfileDefinition] = {
    "generic": GENERIC,
    "codex": CODEX,
}

DEFAULT_PROFILE_ID = "generic"


def resolve_profile(profile_id: str | None) -> ProfileDefinition:
    """Return the ProfileDefinition for *profile_id*.

    Falls back to GENERIC for unknown or None values.
    Never raises — invalid profile_id silently degrades to generic.

    Args:
        profile_id: A profile identifier string (e.g. "generic", "codex").

    Returns:
        The matching ProfileDefinition, or GENERIC as fallback.
    """
    if not profile_id:
        return GENERIC
    return PROFILES.get(profile_id, GENERIC)


def list_profiles() -> list[ProfileDefinition]:
    """Return all registered profiles in insertion order."""
    return list(PROFILES.values())


def validate_profile_surfaces(root: Path, profile: ProfileDefinition) -> list[str]:
    """Return a list of missing expected surfaces for *profile* in *root*.

    Args:
        root: Repo root directory.
        profile: Profile to check against.

    Returns:
        List of surface paths (relative to root) that do not exist.
        Empty list means all expected surfaces are present.
    """
    missing: list[str] = []
    for surface in profile.expected_surfaces:
        if not (root / surface).exists():
            missing.append(surface)
    return missing
