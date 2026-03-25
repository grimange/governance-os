"""Tests for the profile system."""

from pathlib import Path

import pytest

from governance_os.profiles.definitions import CODEX, GENERIC, ProfileDefinition
from governance_os.profiles.registry import (
    PROFILES,
    list_profiles,
    resolve_profile,
    validate_profile_surfaces,
)


# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------


def test_generic_profile_id() -> None:
    assert GENERIC.id == "generic"


def test_codex_profile_id() -> None:
    assert CODEX.id == "codex"


def test_generic_has_no_default_plugins() -> None:
    assert len(GENERIC.default_plugins) == 0


def test_codex_has_codex_instructions_plugin() -> None:
    assert "codex_instructions" in CODEX.default_plugins


def test_generic_expected_surfaces_includes_pipelines_dir() -> None:
    assert "governance/pipelines" in GENERIC.expected_surfaces


def test_codex_expected_surfaces_includes_agents_md() -> None:
    assert "AGENTS.md" in CODEX.expected_surfaces


def test_profiles_are_frozen() -> None:
    with pytest.raises(Exception):
        GENERIC.id = "changed"  # type: ignore[misc]


def test_all_profiles_have_non_empty_description() -> None:
    for p in PROFILES.values():
        assert len(p.description) > 10, f"Empty description for profile {p.id}"


# ---------------------------------------------------------------------------
# resolve_profile
# ---------------------------------------------------------------------------


def test_resolve_profile_generic() -> None:
    p = resolve_profile("generic")
    assert p is GENERIC


def test_resolve_profile_codex() -> None:
    p = resolve_profile("codex")
    assert p is CODEX


def test_resolve_profile_unknown_falls_back_to_generic() -> None:
    p = resolve_profile("nonexistent_profile")
    assert p is GENERIC


def test_resolve_profile_none_falls_back_to_generic() -> None:
    p = resolve_profile(None)
    assert p is GENERIC


def test_resolve_profile_empty_string_falls_back_to_generic() -> None:
    p = resolve_profile("")
    assert p is GENERIC


# ---------------------------------------------------------------------------
# list_profiles
# ---------------------------------------------------------------------------


def test_list_profiles_returns_all() -> None:
    profiles = list_profiles()
    ids = [p.id for p in profiles]
    assert "generic" in ids
    assert "codex" in ids


def test_list_profiles_returns_profile_definition_instances() -> None:
    for p in list_profiles():
        assert isinstance(p, ProfileDefinition)


# ---------------------------------------------------------------------------
# validate_profile_surfaces
# ---------------------------------------------------------------------------


def test_validate_surfaces_all_present(tmp_path: Path) -> None:
    # Create all generic expected surfaces
    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "governance.yaml").write_text("", encoding="utf-8")

    missing = validate_profile_surfaces(tmp_path, GENERIC)
    assert missing == []


def test_validate_surfaces_missing_dir(tmp_path: Path) -> None:
    # Only create partial structure
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "governance.yaml").write_text("", encoding="utf-8")

    missing = validate_profile_surfaces(tmp_path, GENERIC)
    assert "governance/pipelines" in missing


def test_validate_surfaces_codex_missing_agents_md(tmp_path: Path) -> None:
    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "governance.yaml").write_text("", encoding="utf-8")
    # AGENTS.md intentionally absent

    missing = validate_profile_surfaces(tmp_path, CODEX)
    assert "AGENTS.md" in missing


def test_validate_surfaces_codex_all_present(tmp_path: Path) -> None:
    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "governance.yaml").write_text("", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")

    missing = validate_profile_surfaces(tmp_path, CODEX)
    assert missing == []


def test_validate_surfaces_empty_repo_has_all_missing(tmp_path: Path) -> None:
    missing = validate_profile_surfaces(tmp_path, GENERIC)
    assert len(missing) == len(GENERIC.expected_surfaces)


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------


def test_config_profile_defaults_to_generic() -> None:
    from governance_os.config.models import GovernanceConfig

    config = GovernanceConfig()
    assert config.profile == "generic"


def test_config_accepts_profile_field() -> None:
    from governance_os.config.models import GovernanceConfig

    config = GovernanceConfig(profile="codex")
    assert config.profile == "codex"


def test_config_enabled_plugins_defaults_empty() -> None:
    from governance_os.config.models import GovernanceConfig

    config = GovernanceConfig()
    assert config.enabled_plugins == []


def test_config_disabled_plugins_defaults_empty() -> None:
    from governance_os.config.models import GovernanceConfig

    config = GovernanceConfig()
    assert config.disabled_plugins == []


def test_config_with_plugins(tmp_path: Path) -> None:
    from governance_os.config.loader import load_config

    (tmp_path / "governance.yaml").write_text(
        "profile: codex\nenabled_plugins:\n  - doctrine\ndisabled_plugins:\n  - skills\n",
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    assert config.profile == "codex"
    assert "doctrine" in config.enabled_plugins
    assert "skills" in config.disabled_plugins


# ---------------------------------------------------------------------------
# API integration
# ---------------------------------------------------------------------------


def test_api_profile_list() -> None:
    import governance_os.api as api

    profiles = api.profile_list()
    assert any(p.id == "generic" for p in profiles)
    assert any(p.id == "codex" for p in profiles)


def test_api_profile_show_known() -> None:
    import governance_os.api as api

    p = api.profile_show("codex")
    assert p is not None
    assert p.id == "codex"


def test_api_profile_show_unknown_returns_none() -> None:
    import governance_os.api as api

    p = api.profile_show("notexist")
    assert p is None


def test_api_profile_validate_generic_all_present(tmp_path: Path) -> None:
    import governance_os.api as api

    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "governance.yaml").write_text("profile: generic\n", encoding="utf-8")

    profile, missing = api.profile_validate(tmp_path)
    assert profile.id == "generic"
    assert missing == []


def test_api_profile_validate_codex_missing_agents_md(tmp_path: Path) -> None:
    import governance_os.api as api

    (tmp_path / "governance" / "pipelines").mkdir(parents=True)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "governance.yaml").write_text("profile: codex\n", encoding="utf-8")

    profile, missing = api.profile_validate(tmp_path)
    assert profile.id == "codex"
    assert "AGENTS.md" in missing


# ---------------------------------------------------------------------------
# Init integration — Codex profile creates AGENTS.md
# ---------------------------------------------------------------------------


def test_init_codex_creates_agents_md(tmp_path: Path) -> None:
    from governance_os.scaffolding.init import init_repo

    init_repo(tmp_path, level="standard", profile="codex")
    assert (tmp_path / "AGENTS.md").exists()
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Codex" in content


def test_init_generic_does_not_create_agents_md(tmp_path: Path) -> None:
    from governance_os.scaffolding.init import init_repo

    init_repo(tmp_path, level="standard", profile="generic")
    assert not (tmp_path / "AGENTS.md").exists()
