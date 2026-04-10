"""Tests for multi-agent scaffold and audit."""

from pathlib import Path

import pytest

from governance_os.audit.core import audit_multi_agent
from governance_os.scaffolding.init import init_repo


# ---------------------------------------------------------------------------
# Scaffold — codex:multi-agent
# ---------------------------------------------------------------------------


def test_multi_agent_scaffold_creates_agent_definitions(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / ".codex" / "agents" / "planner.toml").exists()
    assert (tmp_path / ".codex" / "agents" / "implementer.toml").exists()
    assert (tmp_path / ".codex" / "agents" / "reviewer.toml").exists()


def test_multi_agent_scaffold_creates_role_contracts(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / "docs" / "governance" / "agents" / "planner.md").exists()
    assert (tmp_path / "docs" / "governance" / "agents" / "implementer.md").exists()
    assert (tmp_path / "docs" / "governance" / "agents" / "reviewer.md").exists()


def test_multi_agent_scaffold_creates_workflow_contract(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / "docs" / "contracts" / "multi-agent-workflow.md").exists()


def test_multi_agent_scaffold_creates_handoffs_dir(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / "artifacts" / "governance" / "handoffs").is_dir()


def test_multi_agent_scaffold_creates_reviews_dir(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / "artifacts" / "governance" / "reviews").is_dir()


def test_multi_agent_scaffold_also_creates_agents_md(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / "AGENTS.md").exists()


def test_multi_agent_scaffold_also_creates_codex_config(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / ".codex" / "config.toml").exists()


def test_multi_agent_scaffold_also_creates_sessions(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / "governance" / "sessions").is_dir()


def test_multi_agent_scaffold_inherits_governed_structure(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "governance" / "skills").is_dir()
    assert (tmp_path / "governance" / "doctrine").is_dir()
    assert (tmp_path / "artifacts" / "governance").is_dir()


def test_multi_agent_scaffold_result_fields(tmp_path):
    result = init_repo(tmp_path, profile="codex", template="multi-agent")
    assert result.profile == "codex"
    assert result.template == "multi-agent"
    assert result.level == "governed"


def test_multi_agent_governance_yaml_has_plugin_enabled(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "multi_agent" in content
    assert "enabled_plugins" in content


def test_multi_agent_governance_yaml_has_codex_profile(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "profile: codex" in content


def test_multi_agent_role_toml_content(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    planner = (tmp_path / ".codex" / "agents" / "planner.toml").read_text(encoding="utf-8")
    assert 'id = "planner"' in planner
    implementer = (tmp_path / ".codex" / "agents" / "implementer.toml").read_text(encoding="utf-8")
    assert 'id = "implementer"' in implementer
    reviewer = (tmp_path / ".codex" / "agents" / "reviewer.toml").read_text(encoding="utf-8")
    assert 'id = "reviewer"' in reviewer


def test_multi_agent_role_contracts_content(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    planner = (tmp_path / "docs" / "governance" / "agents" / "planner.md").read_text(encoding="utf-8")
    assert "Planner" in planner
    assert "Forbidden Actions" in planner
    reviewer = (tmp_path / "docs" / "governance" / "agents" / "reviewer.md").read_text(encoding="utf-8")
    assert "govos preflight" in reviewer


def test_multi_agent_workflow_contract_content(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    content = (tmp_path / "docs" / "contracts" / "multi-agent-workflow.md").read_text(encoding="utf-8")
    assert "planner" in content.lower()
    assert "implementer" in content.lower()
    assert "reviewer" in content.lower()
    assert "Completion Criteria" in content


def test_multi_agent_is_invalid_for_generic_profile(tmp_path):
    with pytest.raises(ValueError, match="requires --profile codex"):
        init_repo(tmp_path, profile="generic", template="multi-agent")


def test_multi_agent_is_invalid_for_unknown_profile(tmp_path):
    # Unknown profile fails on profile validation before reaching template check
    with pytest.raises(ValueError, match="Invalid profile"):
        init_repo(tmp_path, profile="unknown", template="multi-agent")


def test_multi_agent_agents_md_references_role_contracts(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "docs/governance/agents/" in content
    assert "docs/contracts/multi-agent-workflow.md" in content


def test_multi_agent_agents_md_references_all_roles(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "planner" in content
    assert "implementer" in content
    assert "reviewer" in content


def test_multi_agent_agents_md_references_audit_command(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "govos audit multi-agent" in content


def test_minimal_template_agents_md_does_not_reference_roles(tmp_path):
    """Non-multi-agent Codex repos should get the standard AGENTS.md."""
    init_repo(tmp_path, profile="codex", template="minimal")
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "docs/governance/agents/" not in content
    assert "planner" not in content


def test_multi_agent_scaffold_is_idempotent(tmp_path):
    init_repo(tmp_path, profile="codex", template="multi-agent")
    result2 = init_repo(tmp_path, profile="codex", template="multi-agent")
    assert len(result2.skipped_files) > 0
    assert len(result2.created_files) == 0


# ---------------------------------------------------------------------------
# Audit — audit_multi_agent()
# ---------------------------------------------------------------------------


def _scaffold_multi_agent(root: Path) -> None:
    init_repo(root, profile="codex", template="multi-agent")


def test_audit_multi_agent_passes_on_complete_setup(tmp_path):
    _scaffold_multi_agent(tmp_path)
    result = audit_multi_agent(tmp_path)
    assert result.mode == "multi-agent"
    assert result.error_count == 0
    # May have INFO findings (artifact dirs); no errors or warnings on clean scaffold
    assert result.warning_count == 0


def test_audit_multi_agent_missing_agents_dir(tmp_path):
    # No multi-agent scaffold at all
    result = audit_multi_agent(tmp_path)
    codes = [f.code for f in result.findings]
    assert "MULTIAGENT_SETUP_MISSING" in codes


def test_audit_multi_agent_missing_agents_dir_is_warning(tmp_path):
    from governance_os.models.issue import Severity
    result = audit_multi_agent(tmp_path)
    missing = next(f for f in result.findings if f.code == "MULTIAGENT_SETUP_MISSING")
    assert missing.severity == Severity.WARNING


def test_audit_multi_agent_missing_agents_dir_returns_early(tmp_path):
    # When agents dir is missing, should return early with just one finding
    result = audit_multi_agent(tmp_path)
    assert len(result.findings) == 1


def test_audit_multi_agent_missing_role_def(tmp_path):
    _scaffold_multi_agent(tmp_path)
    (tmp_path / ".codex" / "agents" / "planner.toml").unlink()
    result = audit_multi_agent(tmp_path)
    codes = [f.code for f in result.findings]
    assert "MULTIAGENT_MISSING_ROLE_DEF" in codes


def test_audit_multi_agent_missing_reviewer_is_error(tmp_path):
    from governance_os.models.issue import Severity
    _scaffold_multi_agent(tmp_path)
    (tmp_path / ".codex" / "agents" / "reviewer.toml").unlink()
    result = audit_multi_agent(tmp_path)
    reviewer_finding = next(
        f for f in result.findings if f.code == "MULTIAGENT_MISSING_REVIEWER"
    )
    assert reviewer_finding.severity == Severity.ERROR


def test_audit_multi_agent_missing_reviewer_fails(tmp_path):
    _scaffold_multi_agent(tmp_path)
    (tmp_path / ".codex" / "agents" / "reviewer.toml").unlink()
    result = audit_multi_agent(tmp_path)
    assert not result.passed


def test_audit_multi_agent_missing_role_contract(tmp_path):
    _scaffold_multi_agent(tmp_path)
    (tmp_path / "docs" / "governance" / "agents" / "planner.md").unlink()
    result = audit_multi_agent(tmp_path)
    codes = [f.code for f in result.findings]
    assert "MULTIAGENT_MISSING_ROLE_CONTRACT" in codes


def test_audit_multi_agent_empty_role_contract(tmp_path):
    _scaffold_multi_agent(tmp_path)
    (tmp_path / "docs" / "governance" / "agents" / "implementer.md").write_text("", encoding="utf-8")
    result = audit_multi_agent(tmp_path)
    codes = [f.code for f in result.findings]
    assert "MULTIAGENT_EMPTY_ROLE_CONTRACT" in codes


def test_audit_multi_agent_missing_workflow(tmp_path):
    _scaffold_multi_agent(tmp_path)
    (tmp_path / "docs" / "contracts" / "multi-agent-workflow.md").unlink()
    result = audit_multi_agent(tmp_path)
    codes = [f.code for f in result.findings]
    assert "MULTIAGENT_MISSING_WORKFLOW" in codes


def test_audit_multi_agent_missing_handoffs_dir(tmp_path):
    from governance_os.models.issue import Severity
    _scaffold_multi_agent(tmp_path)
    import shutil
    shutil.rmtree(tmp_path / "artifacts" / "governance" / "handoffs")
    result = audit_multi_agent(tmp_path)
    codes = [f.code for f in result.findings]
    assert "MULTIAGENT_MISSING_HANDOFFS_DIR" in codes
    finding = next(f for f in result.findings if f.code == "MULTIAGENT_MISSING_HANDOFFS_DIR")
    assert finding.severity == Severity.INFO


def test_audit_multi_agent_missing_reviews_dir(tmp_path):
    from governance_os.models.issue import Severity
    _scaffold_multi_agent(tmp_path)
    import shutil
    shutil.rmtree(tmp_path / "artifacts" / "governance" / "reviews")
    result = audit_multi_agent(tmp_path)
    codes = [f.code for f in result.findings]
    assert "MULTIAGENT_MISSING_REVIEWS_DIR" in codes


def test_audit_multi_agent_role_mismatch_extra_role(tmp_path):
    _scaffold_multi_agent(tmp_path)
    # Add a role definition with no corresponding contract
    (tmp_path / ".codex" / "agents" / "specialist.toml").write_text(
        '[agent]\nid = "specialist"\n', encoding="utf-8"
    )
    result = audit_multi_agent(tmp_path)
    codes = [f.code for f in result.findings]
    assert "MULTIAGENT_ROLE_MISMATCH" in codes


def test_audit_multi_agent_mode_field(tmp_path):
    _scaffold_multi_agent(tmp_path)
    result = audit_multi_agent(tmp_path)
    assert result.mode == "multi-agent"


def test_audit_multi_agent_all_findings_have_codes(tmp_path):
    result = audit_multi_agent(tmp_path)
    for finding in result.findings:
        assert finding.code.startswith("MULTIAGENT_")


# ---------------------------------------------------------------------------
# api.audit dispatcher
# ---------------------------------------------------------------------------


def test_api_audit_multi_agent_mode(tmp_path):
    import governance_os.api as api
    result = api.audit(tmp_path, mode="multi-agent")
    assert result.mode == "multi-agent"


def test_api_audit_unsupported_mode_still_raises(tmp_path):
    import governance_os.api as api
    with pytest.raises(ValueError, match="Unsupported audit mode"):
        api.audit(tmp_path, mode="nonexistent")


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


def test_multi_agent_plugin_is_registered():
    from governance_os.plugins.registry import _PLUGIN_REGISTRY
    assert "multi_agent" in _PLUGIN_REGISTRY


def test_multi_agent_plugin_run_checks_on_empty_repo(tmp_path):
    from governance_os.plugins.registry import _PLUGIN_REGISTRY
    plugin = _PLUGIN_REGISTRY["multi_agent"]
    issues = plugin.run_checks(tmp_path, [])
    assert len(issues) == 1
    assert issues[0].code == "MULTIAGENT_SETUP_MISSING"
    assert issues[0].source == "multi_agent"


def test_multi_agent_plugin_passes_on_complete_setup(tmp_path):
    from governance_os.plugins.registry import _PLUGIN_REGISTRY
    _scaffold_multi_agent(tmp_path)
    plugin = _PLUGIN_REGISTRY["multi_agent"]
    issues = plugin.run_checks(tmp_path, [])
    errors_and_warnings = [i for i in issues if i.severity.value in ("error", "warning")]
    assert not errors_and_warnings


# ---------------------------------------------------------------------------
# Profile definition
# ---------------------------------------------------------------------------


def test_codex_profile_supports_multi_agent_template():
    from governance_os.profiles.definitions import CODEX
    assert "multi-agent" in CODEX.supported_templates


def test_generic_profile_does_not_support_multi_agent_template():
    from governance_os.profiles.definitions import GENERIC
    assert "multi-agent" not in GENERIC.supported_templates
