"""Tests for the internal plugin system."""

from pathlib import Path

import pytest

from governance_os.models.issue import Severity
from governance_os.plugins.base import Plugin
from governance_os.plugins.codex_instructions import CodexInstructionsPlugin
from governance_os.plugins.doctrine_plugin import DoctrinePlugin
from governance_os.plugins.registry import (
    _PLUGIN_REGISTRY,
    list_plugins,
    resolve_active_plugins,
    run_plugin_checks,
)
from governance_os.plugins.skills_plugin import SkillsPlugin


def _no_pipelines() -> list:
    return []


# ---------------------------------------------------------------------------
# Plugin registry integrity
# ---------------------------------------------------------------------------


def test_all_registered_plugins_have_plugin_id() -> None:
    for pid, plugin in _PLUGIN_REGISTRY.items():
        assert plugin.plugin_id == pid, f"Plugin {pid} has mismatched plugin_id"


def test_all_registered_plugins_have_name() -> None:
    for plugin in _PLUGIN_REGISTRY.values():
        assert plugin.name, f"Plugin {plugin.plugin_id} has empty name"


def test_all_registered_plugins_have_description() -> None:
    for plugin in _PLUGIN_REGISTRY.values():
        assert plugin.description, f"Plugin {plugin.plugin_id} has empty description"


def test_list_plugins_returns_all() -> None:
    plugins = list_plugins()
    ids = [p.plugin_id for p in plugins]
    assert "authority" in ids
    assert "doctrine" in ids
    assert "skills" in ids
    assert "codex_instructions" in ids


def test_all_plugins_are_plugin_instances() -> None:
    for plugin in list_plugins():
        assert isinstance(plugin, Plugin)


# ---------------------------------------------------------------------------
# resolve_active_plugins
# ---------------------------------------------------------------------------


def test_resolve_generic_profile_no_defaults() -> None:
    active = resolve_active_plugins("generic", [], [])
    assert active == []


def test_resolve_codex_profile_includes_codex_instructions() -> None:
    active = resolve_active_plugins("codex", [], [])
    assert "codex_instructions" in active


def test_resolve_enabled_plugins_appended() -> None:
    active = resolve_active_plugins("generic", ["authority"], [])
    assert "authority" in active


def test_resolve_disabled_plugins_removed() -> None:
    active = resolve_active_plugins("codex", [], ["codex_instructions"])
    assert "codex_instructions" not in active


def test_resolve_no_duplicates() -> None:
    # codex includes codex_instructions; enabling it again should not duplicate
    active = resolve_active_plugins("codex", ["codex_instructions"], [])
    assert active.count("codex_instructions") == 1


def test_resolve_unknown_plugin_id_ignored() -> None:
    active = resolve_active_plugins("generic", ["nonexistent_plugin"], [])
    assert "nonexistent_plugin" not in active


def test_resolve_disabled_takes_precedence_over_enabled() -> None:
    active = resolve_active_plugins("generic", ["authority"], ["authority"])
    assert "authority" not in active


def test_resolve_order_is_deterministic() -> None:
    a = resolve_active_plugins("codex", ["authority", "doctrine"], [])
    b = resolve_active_plugins("codex", ["authority", "doctrine"], [])
    assert a == b


def test_resolve_profile_defaults_before_enabled() -> None:
    """Profile defaults appear first in the activation order."""
    active = resolve_active_plugins("codex", ["authority"], [])
    assert active.index("codex_instructions") < active.index("authority")


# ---------------------------------------------------------------------------
# CodexInstructionsPlugin
# ---------------------------------------------------------------------------


def test_codex_plugin_missing_agents_md(tmp_path: Path) -> None:
    plugin = CodexInstructionsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    codes = [i.code for i in issues]
    assert "CODEX_MISSING_AGENTS_MD" in codes


def test_codex_plugin_empty_agents_md(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("", encoding="utf-8")
    plugin = CodexInstructionsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    codes = [i.code for i in issues]
    assert "CODEX_EMPTY_AGENTS_MD" in codes


def test_codex_plugin_sparse_agents_md(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Title\n", encoding="utf-8")
    plugin = CodexInstructionsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    codes = [i.code for i in issues]
    assert "CODEX_AGENTS_MD_SPARSE" in codes


def test_codex_plugin_valid_agents_md_no_issues(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS\n\nLine 1.\nLine 2.\nLine 3.\nLine 4.\n",
        encoding="utf-8",
    )
    plugin = CodexInstructionsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    assert issues == []


def test_codex_plugin_issues_have_source_field(tmp_path: Path) -> None:
    plugin = CodexInstructionsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    for i in issues:
        assert i.source == "codex_instructions"


def test_codex_plugin_missing_agents_md_is_warning(tmp_path: Path) -> None:
    plugin = CodexInstructionsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    assert all(i.severity == Severity.WARNING for i in issues if i.code == "CODEX_MISSING_AGENTS_MD")


# ---------------------------------------------------------------------------
# DoctrinePlugin
# ---------------------------------------------------------------------------


def test_doctrine_plugin_missing_doctrine(tmp_path: Path) -> None:
    plugin = DoctrinePlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    codes = [i.code for i in issues]
    assert "DOCTRINE_MISSING" in codes


def test_doctrine_plugin_valid_doctrine_no_issues(tmp_path: Path) -> None:
    doctrine_dir = tmp_path / "governance" / "doctrine"
    doctrine_dir.mkdir(parents=True)
    (doctrine_dir / "doctrine.md").write_text("# Doctrine\n\n1. Clarity.\n", encoding="utf-8")
    plugin = DoctrinePlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    assert not any(i.severity == Severity.ERROR for i in issues)


def test_doctrine_plugin_issues_have_source_field(tmp_path: Path) -> None:
    plugin = DoctrinePlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    for i in issues:
        assert i.source == "doctrine"


# ---------------------------------------------------------------------------
# SkillsPlugin
# ---------------------------------------------------------------------------


def test_skills_plugin_no_skills_dir_returns_info(tmp_path: Path) -> None:
    plugin = SkillsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    # SKILLS_DIR_NOT_FOUND is INFO severity — not an error
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert not errors


def test_skills_plugin_valid_skills_no_errors(tmp_path: Path) -> None:
    skills_dir = tmp_path / "governance" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "python.md").write_text("# Python\n\nCore Python skill.\n", encoding="utf-8")
    plugin = SkillsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert not errors


def test_skills_plugin_issues_have_source_field(tmp_path: Path) -> None:
    plugin = SkillsPlugin()
    issues = plugin.run_checks(tmp_path, _no_pipelines())
    for i in issues:
        assert i.source == "skills"


# ---------------------------------------------------------------------------
# run_plugin_checks
# ---------------------------------------------------------------------------


def test_run_plugin_checks_generic_no_active_plugins(tmp_path: Path) -> None:
    check_names, issues = run_plugin_checks(tmp_path, [], "generic", [], [])
    assert check_names == []
    assert issues == []


def test_run_plugin_checks_codex_runs_codex_instructions(tmp_path: Path) -> None:
    check_names, issues = run_plugin_checks(tmp_path, [], "codex", [], [])
    assert "codex_instructions" in check_names


def test_run_plugin_checks_enabled_plugins_runs_them(tmp_path: Path) -> None:
    check_names, issues = run_plugin_checks(tmp_path, [], "generic", ["doctrine"], [])
    assert "doctrine" in check_names


def test_run_plugin_checks_disabled_plugins_not_run(tmp_path: Path) -> None:
    check_names, issues = run_plugin_checks(
        tmp_path, [], "codex", [], ["codex_instructions"]
    )
    assert "codex_instructions" not in check_names


def test_run_plugin_checks_unknown_profile_treated_as_generic(tmp_path: Path) -> None:
    check_names, issues = run_plugin_checks(tmp_path, [], "nonexistent", [], [])
    assert check_names == []


# ---------------------------------------------------------------------------
# Issue source field
# ---------------------------------------------------------------------------


def test_issue_model_has_source_field() -> None:
    from governance_os.models.issue import Issue, Severity

    issue = Issue(code="TEST", severity=Severity.INFO, message="test", source="myplugin")
    assert issue.source == "myplugin"


def test_issue_source_defaults_to_none() -> None:
    from governance_os.models.issue import Issue, Severity

    issue = Issue(code="TEST", severity=Severity.INFO, message="test")
    assert issue.source is None


def test_issue_model_copy_with_source() -> None:
    from governance_os.models.issue import Issue, Severity

    original = Issue(code="TEST", severity=Severity.WARNING, message="m")
    updated = original.model_copy(update={"source": "authority"})
    assert updated.source == "authority"
    assert original.source is None  # original unchanged


# ---------------------------------------------------------------------------
# Profile-aware preflight integration
# ---------------------------------------------------------------------------


def test_preflight_generic_no_plugin_checks(tmp_path: Path) -> None:
    """Generic profile runs no plugin checks by default."""
    from governance_os.config.models import GovernanceConfig
    import governance_os.api as api

    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    (tmp_path / "governance.yaml").write_text("profile: generic\n", encoding="utf-8")
    config = GovernanceConfig(profile="generic")
    result = api.preflight(tmp_path, config=config)
    # Check that no plugin checks appear in checks list by default
    plugin_ids = {"authority", "doctrine", "skills", "codex_instructions"}
    plugin_checks_run = set(result.checks) & plugin_ids
    assert not plugin_checks_run


def test_preflight_codex_runs_codex_instructions(tmp_path: Path) -> None:
    """Codex profile activates codex_instructions plugin during preflight."""
    from governance_os.config.models import GovernanceConfig
    import governance_os.api as api

    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    (tmp_path / "governance.yaml").write_text("profile: codex\n", encoding="utf-8")
    config = GovernanceConfig(profile="codex")
    result = api.preflight(tmp_path, config=config)
    assert "codex_instructions" in result.checks


def test_preflight_codex_missing_agents_md_produces_finding(tmp_path: Path) -> None:
    """Codex profile preflight reports CODEX_MISSING_AGENTS_MD when AGENTS.md is absent."""
    from governance_os.config.models import GovernanceConfig
    import governance_os.api as api

    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    config = GovernanceConfig(profile="codex")
    result = api.preflight(tmp_path, config=config)
    codes = [i.code for i in result.issues]
    assert "CODEX_MISSING_AGENTS_MD" in codes


def test_preflight_include_authority_does_not_duplicate_authority_plugin(tmp_path: Path) -> None:
    """When include_authority=True, the authority plugin is suppressed to avoid duplication."""
    from governance_os.config.models import GovernanceConfig
    import governance_os.api as api

    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    config = GovernanceConfig(profile="generic", enabled_plugins=["authority"])
    result = api.preflight(tmp_path, config=config, include_authority=True)
    # "authority" should appear exactly once in checks
    assert result.checks.count("authority") == 1
