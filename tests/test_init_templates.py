"""Tests for profile + template scaffold combinations."""

import pytest

from governance_os.scaffolding.init import (
    ScaffoldResult,
    format_result,
    init_repo,
)


# ---------------------------------------------------------------------------
# generic:minimal
# ---------------------------------------------------------------------------


def test_generic_minimal_creates_base_structure(tmp_path):
    result = init_repo(tmp_path, profile="generic", template="minimal")
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "governance.yaml").exists()


def test_generic_minimal_does_not_create_docs(tmp_path):
    init_repo(tmp_path, profile="generic", template="minimal")
    assert not (tmp_path / "docs" / "governance").exists()


def test_generic_minimal_does_not_create_sessions(tmp_path):
    init_repo(tmp_path, profile="generic", template="minimal")
    assert not (tmp_path / "governance" / "sessions").exists()


def test_generic_minimal_does_not_create_agents_md(tmp_path):
    init_repo(tmp_path, profile="generic", template="minimal")
    assert not (tmp_path / "AGENTS.md").exists()


def test_generic_minimal_result_fields(tmp_path):
    result = init_repo(tmp_path, profile="generic", template="minimal")
    assert result.profile == "generic"
    assert result.level == "minimal"
    assert result.template == "minimal"


def test_generic_minimal_governance_yaml_has_profile(tmp_path):
    init_repo(tmp_path, profile="generic", template="minimal")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "profile: generic" in content
    assert "pipelines_dir" in content
    assert "contracts_glob" in content


def test_generic_minimal_governance_yaml_no_governed_sections(tmp_path):
    init_repo(tmp_path, profile="generic", template="minimal")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "registry:" not in content
    assert "audit:" not in content


# ---------------------------------------------------------------------------
# generic:governed
# ---------------------------------------------------------------------------


def test_generic_governed_creates_extended_structure(tmp_path):
    result = init_repo(tmp_path, profile="generic", template="governed")
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "governance" / "skills").is_dir()
    assert (tmp_path / "artifacts" / "governance").is_dir()
    assert (tmp_path / "docs" / "governance").is_dir()


def test_generic_governed_creates_doctrine(tmp_path):
    init_repo(tmp_path, profile="generic", template="governed")
    assert (tmp_path / "governance" / "doctrine" / "doctrine.md").exists()


def test_generic_governed_does_not_create_agents_md(tmp_path):
    init_repo(tmp_path, profile="generic", template="governed")
    assert not (tmp_path / "AGENTS.md").exists()


def test_generic_governed_governance_yaml_has_governed_sections(tmp_path):
    init_repo(tmp_path, profile="generic", template="governed")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "profile: generic" in content
    assert "registry:" in content
    assert "audit:" in content


# ---------------------------------------------------------------------------
# codex:minimal
# ---------------------------------------------------------------------------


def test_codex_minimal_creates_base_structure(tmp_path):
    result = init_repo(tmp_path, profile="codex", template="minimal")
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "governance.yaml").exists()
    assert result.profile == "codex"
    assert result.template == "minimal"


def test_codex_minimal_creates_agents_md(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    assert (tmp_path / "AGENTS.md").exists()


def test_codex_minimal_agents_md_is_short(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    lines = [l for l in content.splitlines() if l.strip()]
    # Should be a brief operational file, not a doctrine manual
    assert len(lines) < 50, f"AGENTS.md too large: {len(lines)} non-empty lines"


def test_codex_minimal_agents_md_references_governance_surfaces(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "governance/pipelines" in content
    assert "governance.yaml" in content
    assert "govos preflight" in content


def test_codex_minimal_creates_codex_config_toml(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    assert (tmp_path / ".codex" / "config.toml").exists()


def test_codex_config_toml_content(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    content = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'profile = "codex"' in content
    assert "contracts" in content
    assert "preflight" in content


def test_codex_minimal_creates_sessions_dir(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    assert (tmp_path / "governance" / "sessions" / "session-template.md").exists()


def test_codex_minimal_governance_yaml_has_codex_profile(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "profile: codex" in content


def test_codex_minimal_does_not_create_docs(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    assert not (tmp_path / "docs" / "governance").exists()


def test_codex_minimal_does_not_create_skills_dir(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    assert not (tmp_path / "governance" / "skills").is_dir()


def test_codex_minimal_does_not_create_preflight_skill(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    assert not (tmp_path / "governance" / "skills" / "govos-preflight.skill.md").exists()


# ---------------------------------------------------------------------------
# codex:governed
# ---------------------------------------------------------------------------


def test_codex_governed_creates_full_structure(tmp_path):
    result = init_repo(tmp_path, profile="codex", template="governed")
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "governance" / "skills").is_dir()
    assert (tmp_path / "artifacts" / "governance").is_dir()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".codex" / "config.toml").exists()
    assert result.profile == "codex"
    assert result.template == "governed"


def test_codex_governed_creates_preflight_skill(tmp_path):
    init_repo(tmp_path, profile="codex", template="governed")
    skill_path = tmp_path / "governance" / "skills" / "govos-preflight.skill.md"
    assert skill_path.exists()


def test_codex_governed_preflight_skill_content(tmp_path):
    init_repo(tmp_path, profile="codex", template="governed")
    content = (
        tmp_path / "governance" / "skills" / "govos-preflight.skill.md"
    ).read_text(encoding="utf-8")
    assert "govos preflight" in content
    assert "ERROR" in content


def test_codex_governed_creates_doctrine(tmp_path):
    init_repo(tmp_path, profile="codex", template="governed")
    assert (tmp_path / "governance" / "doctrine" / "doctrine.md").exists()


def test_codex_governed_governance_yaml_has_governed_sections(tmp_path):
    init_repo(tmp_path, profile="codex", template="governed")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "profile: codex" in content
    assert "registry:" in content
    assert "audit:" in content


def test_codex_governed_agents_md_not_redundant_with_skill(tmp_path):
    """AGENTS.md should not contain the full preflight procedure — that lives in the skill."""
    init_repo(tmp_path, profile="codex", template="governed")
    agents_content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    # AGENTS.md should reference preflight but not contain detailed step lists from the skill
    skill_content = (
        tmp_path / "governance" / "skills" / "govos-preflight.skill.md"
    ).read_text(encoding="utf-8")
    # The skill contains a numbered procedure; AGENTS.md should not duplicate it verbatim
    assert len(agents_content) < len(skill_content) * 3


# ---------------------------------------------------------------------------
# Invalid combinations
# ---------------------------------------------------------------------------


def test_invalid_template_raises(tmp_path):
    with pytest.raises(ValueError, match="Invalid template"):
        init_repo(tmp_path, profile="generic", template="extended")


def test_invalid_template_message_shows_valid_options(tmp_path):
    with pytest.raises(ValueError) as exc_info:
        init_repo(tmp_path, profile="generic", template="nonexistent")
    assert "minimal" in str(exc_info.value)
    assert "governed" in str(exc_info.value)


def test_unknown_profile_raises_value_error(tmp_path):
    # Unknown profile now raises ValueError — strict validation in plan_scaffold()
    with pytest.raises(ValueError, match="Invalid profile"):
        init_repo(tmp_path, profile="unknown", template="minimal")


# ---------------------------------------------------------------------------
# Backward compatibility — --level still works
# ---------------------------------------------------------------------------


def test_level_minimal_still_works(tmp_path):
    result = init_repo(tmp_path, level="minimal")
    assert result.level == "minimal"
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert not (tmp_path / "docs" / "governance").exists()


def test_level_governed_still_works(tmp_path):
    result = init_repo(tmp_path, level="governed")
    assert result.level == "governed"
    assert (tmp_path / "governance" / "doctrine" / "doctrine.md").exists()


def test_template_takes_precedence_over_level(tmp_path):
    # --template minimal overrides --level governed
    result = init_repo(tmp_path, level="governed", template="minimal")
    assert result.level == "minimal"
    assert result.template == "minimal"
    assert not (tmp_path / "docs" / "governance").exists()


# ---------------------------------------------------------------------------
# governance.yaml content
# ---------------------------------------------------------------------------


def test_governed_governance_yaml_has_authority_section(tmp_path):
    init_repo(tmp_path, profile="generic", template="governed")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "authority:" in content
    assert "required_roots:" in content


def test_minimal_governance_yaml_no_authority_section(tmp_path):
    init_repo(tmp_path, profile="generic", template="minimal")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "authority:" not in content


# ---------------------------------------------------------------------------
# format_result output
# ---------------------------------------------------------------------------


def test_format_result_shows_profile_and_template(tmp_path):
    result = init_repo(tmp_path, profile="codex", template="minimal")
    output = format_result(result)
    assert "codex" in output
    assert "minimal" in output


def test_format_result_shows_created_files(tmp_path):
    result = init_repo(tmp_path, profile="codex", template="minimal")
    output = format_result(result)
    assert "AGENTS.md" in output
    assert ".codex" in output


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_codex_minimal_is_idempotent(tmp_path):
    init_repo(tmp_path, profile="codex", template="minimal")
    result2 = init_repo(tmp_path, profile="codex", template="minimal")
    assert len(result2.skipped_files) > 0
    assert len(result2.created_files) == 0


def test_codex_governed_is_idempotent(tmp_path):
    init_repo(tmp_path, profile="codex", template="governed")
    result2 = init_repo(tmp_path, profile="codex", template="governed")
    assert len(result2.skipped_files) > 0
    assert len(result2.created_files) == 0
