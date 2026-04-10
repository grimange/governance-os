"""Plugin registry and activation logic for governance-os.

All plugins are statically registered. There is no dynamic loading.

Plugin activation order (deterministic):
  1. Start with the profile's default_plugins (ordered list).
  2. Append enabled_plugins from repo config (deduplicated, in order listed).
  3. Remove disabled_plugins from repo config.

Only plugins present in PLUGIN_REGISTRY can be activated.
Unknown plugin IDs in config emit a WARNING issue via validate_plugin_ids().
"""

from __future__ import annotations

from pathlib import Path

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline
from governance_os.plugins.authority_plugin import AuthorityPlugin
from governance_os.plugins.base import Plugin
from governance_os.plugins.codex_instructions import CodexInstructionsPlugin
from governance_os.plugins.doctrine_plugin import DoctrinePlugin
from governance_os.plugins.multi_agent_plugin import MultiAgentPlugin
from governance_os.plugins.skills_plugin import SkillsPlugin
from governance_os.profiles.registry import resolve_profile

# ---------------------------------------------------------------------------
# Static plugin registry
# ---------------------------------------------------------------------------

_PLUGIN_REGISTRY: dict[str, Plugin] = {
    "authority": AuthorityPlugin(),
    "doctrine": DoctrinePlugin(),
    "skills": SkillsPlugin(),
    "codex_instructions": CodexInstructionsPlugin(),
    "multi_agent": MultiAgentPlugin(),
}

# Public alias — same object, stable import surface.
PLUGIN_REGISTRY: dict[str, Plugin] = _PLUGIN_REGISTRY


def list_plugins() -> list[Plugin]:
    """Return all registered plugins in registration order."""
    return list(_PLUGIN_REGISTRY.values())


def is_known_plugin(plugin_id: str) -> bool:
    """Return True if *plugin_id* is registered in the plugin registry.

    Args:
        plugin_id: Plugin identifier to check.

    Returns:
        True when the plugin is registered; False otherwise.
    """
    return plugin_id in _PLUGIN_REGISTRY


def validate_plugin_ids(plugin_ids: list[str]) -> list[Issue]:
    """Return WARNING issues for any plugin IDs that are not registered.

    Callers (e.g. preflight, config validation) use this to surface unknown
    plugin IDs before they are silently dropped by resolve_active_plugins().

    Args:
        plugin_ids: Plugin IDs to validate (from enabled_plugins/disabled_plugins).

    Returns:
        One WARNING Issue per unknown plugin ID.  Empty list when all IDs are valid.
    """
    issues: list[Issue] = []
    for pid in plugin_ids:
        if pid not in _PLUGIN_REGISTRY:
            issues.append(
                Issue(
                    code="PLUGIN_UNKNOWN",
                    severity=Severity.WARNING,
                    message=f"Plugin '{pid}' is not registered and will be ignored.",
                    suggestion=f"Available plugins: {', '.join(sorted(_PLUGIN_REGISTRY))}",
                )
            )
    return issues


def resolve_active_plugins(
    profile_id: str,
    enabled_plugins: list[str],
    disabled_plugins: list[str],
) -> list[str]:
    """Resolve the ordered list of active plugin IDs.

    Activation rules (deterministic):
      1. Start with profile.default_plugins (profile definition order).
      2. Append config enabled_plugins (deduplicated, config order).
      3. Remove config disabled_plugins.
      4. Remove IDs not in _PLUGIN_REGISTRY (unknown plugins are skipped).

    Args:
        profile_id: Effective profile identifier.
        enabled_plugins: Plugin IDs to additionally activate (from config).
        disabled_plugins: Plugin IDs to deactivate (from config).

    Returns:
        Ordered list of active plugin IDs.
    """
    profile = resolve_profile(profile_id)
    seen: set[str] = set()
    ordered: list[str] = []

    for pid in list(profile.default_plugins) + enabled_plugins:
        if pid not in seen:
            seen.add(pid)
            ordered.append(pid)

    active = [pid for pid in ordered if pid not in disabled_plugins]
    return [pid for pid in active if pid in _PLUGIN_REGISTRY]


def run_plugin_checks(
    root: Path,
    pipelines: list[Pipeline],
    profile_id: str,
    enabled_plugins: list[str],
    disabled_plugins: list[str],
) -> tuple[list[str], list[Issue]]:
    """Run all active plugin checks and return (check_names, issues).

    Args:
        root: Repo root directory.
        pipelines: Parsed pipeline contracts.
        profile_id: Effective profile identifier.
        enabled_plugins: Additional plugins from config.
        disabled_plugins: Plugins suppressed by config.

    Returns:
        (check_names, issues) where check_names are the plugin IDs that ran.
    """
    active_ids = resolve_active_plugins(profile_id, enabled_plugins, disabled_plugins)
    check_names: list[str] = []
    all_issues: list[Issue] = []

    for pid in active_ids:
        plugin = _PLUGIN_REGISTRY[pid]
        issues = plugin.run_checks(root, pipelines)
        check_names.append(pid)
        all_issues.extend(issues)

    return check_names, all_issues
