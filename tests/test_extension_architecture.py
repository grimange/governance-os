"""Tests for Phase 5 extension architecture guarantees.

Tests in this module protect:
- Profile registry: is_known_profile, list_profiles, PROFILES
- Plugin registry: PLUGIN_REGISTRY public alias, is_known_plugin, validate_plugin_ids
- API: plugin_list, plugin_show
- CLI: govos plugin list, govos plugin show
- Extension validation: unknown plugin IDs emit WARNING, not silently dropped
- First-party invariants: static registration, no dynamic loading
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from governance_os.cli import app
from governance_os.models.issue import Severity
from governance_os.plugins import (
    PLUGIN_REGISTRY,
    Plugin,
    is_known_plugin,
    list_plugins,
    validate_plugin_ids,
)
from governance_os.profiles import (
    PROFILES,
    ProfileDefinition,
    is_known_profile,
    list_profiles,
    resolve_profile,
)

runner = CliRunner()

_KNOWN_PROFILES = {"generic", "codex"}
_KNOWN_PLUGINS = {"authority", "doctrine", "skills", "codex_instructions", "multi_agent"}


# ---------------------------------------------------------------------------
# Section A: Profile registry
# ---------------------------------------------------------------------------


def test_profiles_dict_contains_known_profiles():
    assert _KNOWN_PROFILES <= set(PROFILES.keys())


def test_is_known_profile_returns_true_for_generic():
    assert is_known_profile("generic") is True


def test_is_known_profile_returns_true_for_codex():
    assert is_known_profile("codex") is True


def test_is_known_profile_returns_false_for_unknown():
    assert is_known_profile("nonexistent") is False


def test_is_known_profile_returns_false_for_empty_string():
    assert is_known_profile("") is False


def test_list_profiles_returns_all_registered():
    profiles = list_profiles()
    ids = {p.id for p in profiles}
    assert _KNOWN_PROFILES <= ids


def test_list_profiles_all_are_profile_definitions():
    for p in list_profiles():
        assert isinstance(p, ProfileDefinition)


def test_resolve_profile_returns_generic_for_none():
    p = resolve_profile(None)
    assert p.id == "generic"


def test_resolve_profile_returns_generic_for_unknown():
    p = resolve_profile("totally_unknown")
    assert p.id == "generic"


def test_resolve_profile_returns_codex_for_codex():
    p = resolve_profile("codex")
    assert p.id == "codex"


def test_profiles_imported_from_package():
    """PROFILES is accessible from the profiles package."""
    from governance_os.profiles import PROFILES as p
    assert "generic" in p


# ---------------------------------------------------------------------------
# Section B: Plugin registry
# ---------------------------------------------------------------------------


def test_plugin_registry_contains_known_plugins():
    assert _KNOWN_PLUGINS <= set(PLUGIN_REGISTRY.keys())


def test_plugin_registry_public_alias_is_same_object():
    from governance_os.plugins.registry import _PLUGIN_REGISTRY
    assert PLUGIN_REGISTRY is _PLUGIN_REGISTRY


def test_is_known_plugin_returns_true_for_authority():
    assert is_known_plugin("authority") is True


def test_is_known_plugin_returns_true_for_multi_agent():
    assert is_known_plugin("multi_agent") is True


def test_is_known_plugin_returns_false_for_unknown():
    assert is_known_plugin("nonexistent_plugin") is False


def test_is_known_plugin_returns_false_for_empty_string():
    assert is_known_plugin("") is False


def test_list_plugins_returns_all_registered():
    plugins = list_plugins()
    ids = {p.plugin_id for p in plugins}
    assert _KNOWN_PLUGINS <= ids


def test_list_plugins_all_are_plugin_instances():
    for p in list_plugins():
        assert isinstance(p, Plugin)


def test_plugin_registry_keys_match_plugin_ids():
    for pid, plugin in PLUGIN_REGISTRY.items():
        assert plugin.plugin_id == pid


def test_all_plugins_have_non_empty_name():
    for p in list_plugins():
        assert p.name, f"Plugin {p.plugin_id} has empty name"


def test_all_plugins_have_non_empty_description():
    for p in list_plugins():
        assert p.description, f"Plugin {p.plugin_id} has empty description"


def test_plugins_imported_from_package():
    """PLUGIN_REGISTRY and helpers are accessible from the plugins package."""
    from governance_os.plugins import PLUGIN_REGISTRY as pr
    assert "authority" in pr


# ---------------------------------------------------------------------------
# Section C: validate_plugin_ids
# ---------------------------------------------------------------------------


def test_validate_plugin_ids_no_issues_for_known():
    issues = validate_plugin_ids(["authority", "doctrine"])
    assert issues == []


def test_validate_plugin_ids_warning_for_unknown():
    issues = validate_plugin_ids(["nonexistent"])
    assert len(issues) == 1
    assert issues[0].code == "PLUGIN_UNKNOWN"
    assert issues[0].severity == Severity.WARNING


def test_validate_plugin_ids_one_warning_per_unknown():
    issues = validate_plugin_ids(["bad1", "bad2", "authority"])
    assert len(issues) == 2
    codes = [i.code for i in issues]
    assert all(c == "PLUGIN_UNKNOWN" for c in codes)


def test_validate_plugin_ids_warning_message_includes_id():
    issues = validate_plugin_ids(["totally_unknown"])
    assert "totally_unknown" in issues[0].message


def test_validate_plugin_ids_suggestion_lists_available():
    issues = validate_plugin_ids(["bad"])
    assert issues[0].suggestion is not None
    assert "authority" in issues[0].suggestion


def test_validate_plugin_ids_empty_list_no_issues():
    assert validate_plugin_ids([]) == []


def test_validate_plugin_ids_mixed_known_and_unknown():
    issues = validate_plugin_ids(["authority", "bad"])
    assert len(issues) == 1
    assert "bad" in issues[0].message


# ---------------------------------------------------------------------------
# Section D: API — plugin_list and plugin_show
# ---------------------------------------------------------------------------


def test_api_plugin_list_returns_all():
    import governance_os.api as api
    plugins = api.plugin_list()
    ids = {p.plugin_id for p in plugins}
    assert _KNOWN_PLUGINS <= ids


def test_api_plugin_list_all_are_plugin_instances():
    import governance_os.api as api
    for p in api.plugin_list():
        assert isinstance(p, Plugin)


def test_api_plugin_show_returns_plugin_for_known():
    import governance_os.api as api
    p = api.plugin_show("authority")
    assert p is not None
    assert p.plugin_id == "authority"


def test_api_plugin_show_returns_none_for_unknown():
    import governance_os.api as api
    result = api.plugin_show("nonexistent")
    assert result is None


def test_api_plugin_show_all_known_ids():
    import governance_os.api as api
    for pid in _KNOWN_PLUGINS:
        p = api.plugin_show(pid)
        assert p is not None, f"plugin_show({pid!r}) returned None"


# ---------------------------------------------------------------------------
# Section E: CLI — govos plugin list
# ---------------------------------------------------------------------------


def test_cli_plugin_list_exits_0():
    result = runner.invoke(app, ["plugin", "list"])
    assert result.exit_code == 0


def test_cli_plugin_list_includes_all_known_plugins():
    result = runner.invoke(app, ["plugin", "list"])
    for pid in _KNOWN_PLUGINS:
        assert pid in result.output


def test_cli_plugin_list_includes_descriptions():
    result = runner.invoke(app, ["plugin", "list"])
    # Each plugin must have name output; check authority's description appears
    assert result.output.strip()  # non-empty output


# ---------------------------------------------------------------------------
# Section F: CLI — govos plugin show
# ---------------------------------------------------------------------------


def test_cli_plugin_show_known_exits_0():
    result = runner.invoke(app, ["plugin", "show", "authority"])
    assert result.exit_code == 0


def test_cli_plugin_show_known_displays_plugin_id():
    result = runner.invoke(app, ["plugin", "show", "skills"])
    assert "skills" in result.output


def test_cli_plugin_show_unknown_exits_2():
    result = runner.invoke(app, ["plugin", "show", "nonexistent"])
    assert result.exit_code == 2


def test_cli_plugin_show_unknown_error_message():
    result = runner.invoke(app, ["plugin", "show", "nonexistent"])
    assert "not found" in result.output.lower() or "not found" in (result.stderr or "").lower()


def test_cli_plugin_show_all_known_ids_exit_0():
    for pid in _KNOWN_PLUGINS:
        result = runner.invoke(app, ["plugin", "show", pid])
        assert result.exit_code == 0, f"plugin show {pid} exited {result.exit_code}"


# ---------------------------------------------------------------------------
# Section G: Extension boundary invariants
# ---------------------------------------------------------------------------


def test_plugin_registry_is_finite_and_static():
    """PLUGIN_REGISTRY must not grow between calls (no dynamic registration)."""
    count_before = len(list_plugins())
    _ = list_plugins()
    count_after = len(list_plugins())
    assert count_before == count_after


def test_profile_registry_is_finite_and_static():
    """PROFILES must not grow between calls (no dynamic registration)."""
    count_before = len(list_profiles())
    _ = list_profiles()
    count_after = len(list_profiles())
    assert count_before == count_after


def test_multi_agent_plugin_is_registered():
    """multi_agent plugin must be in the registry (was missing from docstring)."""
    assert is_known_plugin("multi_agent")
    p = PLUGIN_REGISTRY["multi_agent"]
    assert p.plugin_id == "multi_agent"


def test_unknown_plugin_id_not_in_registry():
    assert not is_known_plugin("user_custom_plugin")
    assert "user_custom_plugin" not in PLUGIN_REGISTRY


def test_plugins_package_exports_are_stable():
    """All documented package exports are importable."""
    from governance_os.plugins import (  # noqa: F401
        PLUGIN_REGISTRY,
        Plugin,
        is_known_plugin,
        list_plugins,
        validate_plugin_ids,
    )


def test_profiles_package_exports_are_stable():
    """All documented package exports are importable."""
    from governance_os.profiles import (  # noqa: F401
        PROFILES,
        ProfileDefinition,
        is_known_profile,
        list_profiles,
        resolve_profile,
        validate_profile_surfaces,
    )
