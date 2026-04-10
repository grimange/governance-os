"""Tests for the Phase 3 scaffold plan API.

Covers:
- plan_scaffold() determinism and validation
- execute_plan() with all three ConflictPolicy values
- validate_scaffold() post-init checks
- format_plan() dry-run display
- Invalid input combinations
- File count assertions per profile/template
"""

from pathlib import Path

import pytest

from governance_os.scaffolding.init import (
    SCAFFOLD_VERSION,
    ConflictPolicy,
    ScaffoldPlan,
    execute_plan,
    format_plan,
    plan_scaffold,
    validate_scaffold,
)


# ---------------------------------------------------------------------------
# plan_scaffold — determinism
# ---------------------------------------------------------------------------


def test_plan_scaffold_deterministic(tmp_path: Path) -> None:
    """plan_scaffold produces identical plans for the same inputs."""
    plan1 = plan_scaffold(tmp_path, profile="generic", template="standard")
    plan2 = plan_scaffold(tmp_path, profile="generic", template="standard")

    assert [d for d in plan1.directories] == [d for d in plan2.directories]
    assert [(f.path, f.content) for f in plan1.files] == [
        (f.path, f.content) for f in plan2.files
    ]


def test_plan_scaffold_version(tmp_path: Path) -> None:
    """plan_scaffold stamps the correct scaffold version."""
    plan = plan_scaffold(tmp_path)
    assert plan.scaffold_version == SCAFFOLD_VERSION


def test_plan_scaffold_sets_profile(tmp_path: Path) -> None:
    plan = plan_scaffold(tmp_path, profile="codex", template="minimal")
    assert plan.profile == "codex"


def test_plan_scaffold_sets_template(tmp_path: Path) -> None:
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    assert plan.template == "minimal"


# ---------------------------------------------------------------------------
# plan_scaffold — file counts per profile/template
# ---------------------------------------------------------------------------


def test_generic_minimal_file_count(tmp_path: Path) -> None:
    """generic:minimal produces exactly 2 files (governance.yaml + example pipeline)."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    assert len(plan.files) == 2


def test_generic_standard_file_count(tmp_path: Path) -> None:
    """generic:standard adds README.governance.md on top of minimal."""
    plan = plan_scaffold(tmp_path, profile="generic", template="standard")
    assert len(plan.files) == 3  # governance.yaml + example + README


def test_generic_governed_file_count(tmp_path: Path) -> None:
    """generic:governed adds doctrine.md on top of standard."""
    plan = plan_scaffold(tmp_path, profile="generic", template="governed")
    # governance.yaml + example + README + doctrine.md
    assert len(plan.files) == 4


def test_codex_minimal_file_count(tmp_path: Path) -> None:
    """codex:minimal adds session template, AGENTS.md, .codex/config.toml."""
    plan = plan_scaffold(tmp_path, profile="codex", template="minimal")
    # governance.yaml + example + session-template + AGENTS.md + config.toml
    assert len(plan.files) == 5


def test_codex_governed_file_count(tmp_path: Path) -> None:
    """codex:governed adds preflight skill on top of codex:standard+doctrine."""
    plan = plan_scaffold(tmp_path, profile="codex", template="governed")
    # governance.yaml + example + README + doctrine + session + AGENTS.md + config + preflight
    assert len(plan.files) == 8


def test_no_duplicate_directories(tmp_path: Path) -> None:
    """plan_scaffold produces no duplicate directory entries."""
    for template in ("minimal", "standard", "governed"):
        plan = plan_scaffold(tmp_path, profile="generic", template=template)
        assert len(plan.directories) == len(set(plan.directories)), (
            f"Duplicate dirs in generic:{template}"
        )

    for template in ("minimal", "standard", "governed", "multi-agent"):
        plan = plan_scaffold(tmp_path, profile="codex", template=template)
        assert len(plan.directories) == len(set(plan.directories)), (
            f"Duplicate dirs in codex:{template}"
        )


# ---------------------------------------------------------------------------
# plan_scaffold — invalid inputs
# ---------------------------------------------------------------------------


def test_invalid_profile_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Invalid profile"):
        plan_scaffold(tmp_path, profile="unknown")


def test_invalid_template_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Invalid template"):
        plan_scaffold(tmp_path, template="nonexistent")


def test_multi_agent_requires_codex_profile(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires --profile codex"):
        plan_scaffold(tmp_path, profile="generic", template="multi-agent")


# ---------------------------------------------------------------------------
# execute_plan — ConflictPolicy.SKIP (default)
# ---------------------------------------------------------------------------


def test_execute_plan_creates_dirs(tmp_path: Path) -> None:
    plan = plan_scaffold(tmp_path, profile="generic", template="standard")
    result = execute_plan(plan)
    for d in plan.directories:
        assert d.is_dir(), f"Expected directory to exist: {d}"


def test_execute_plan_creates_files(tmp_path: Path) -> None:
    plan = plan_scaffold(tmp_path, profile="generic", template="standard")
    result = execute_plan(plan)
    for sf in plan.files:
        assert sf.path.exists(), f"Expected file to exist: {sf.path}"


def test_execute_plan_skip_policy(tmp_path: Path) -> None:
    """SKIP policy leaves existing files unchanged."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    # Pre-write governance.yaml with custom content
    gov_yaml = tmp_path / "governance.yaml"
    gov_yaml.parent.mkdir(parents=True, exist_ok=True)
    gov_yaml.write_text("# custom", encoding="utf-8")

    result = execute_plan(plan, conflict=ConflictPolicy.SKIP)

    assert gov_yaml in result.skipped_files
    assert gov_yaml not in result.created_files
    assert gov_yaml.read_text(encoding="utf-8") == "# custom"


def test_execute_plan_skip_is_idempotent(tmp_path: Path) -> None:
    """Running execute_plan twice with SKIP produces no new files on the second run."""
    plan = plan_scaffold(tmp_path, profile="generic", template="standard")
    execute_plan(plan)
    result2 = execute_plan(plan, conflict=ConflictPolicy.SKIP)
    assert not result2.created_dirs
    assert not result2.created_files
    assert result2.skipped_files


# ---------------------------------------------------------------------------
# execute_plan — ConflictPolicy.OVERWRITE
# ---------------------------------------------------------------------------


def test_execute_plan_overwrite_policy(tmp_path: Path) -> None:
    """OVERWRITE policy replaces existing file content."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    gov_yaml = tmp_path / "governance.yaml"
    gov_yaml.parent.mkdir(parents=True, exist_ok=True)
    gov_yaml.write_text("# old content", encoding="utf-8")

    result = execute_plan(plan, conflict=ConflictPolicy.OVERWRITE)

    assert gov_yaml in result.overwritten_files
    assert gov_yaml not in result.skipped_files
    # Content should now be the planned content, not the old content
    assert gov_yaml.read_text(encoding="utf-8") != "# old content"


# ---------------------------------------------------------------------------
# execute_plan — ConflictPolicy.FAIL
# ---------------------------------------------------------------------------


def test_execute_plan_fail_policy_raises(tmp_path: Path) -> None:
    """FAIL policy raises FileExistsError when a planned file already exists."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    gov_yaml = tmp_path / "governance.yaml"
    gov_yaml.parent.mkdir(parents=True, exist_ok=True)
    gov_yaml.write_text("# existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        execute_plan(plan, conflict=ConflictPolicy.FAIL)


def test_execute_plan_fail_policy_clean_repo(tmp_path: Path) -> None:
    """FAIL policy succeeds on a clean (no pre-existing files) directory."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    result = execute_plan(plan, conflict=ConflictPolicy.FAIL)
    # All files should be created, none skipped or overwritten
    assert result.created_files
    assert not result.skipped_files
    assert not result.overwritten_files


# ---------------------------------------------------------------------------
# validate_scaffold
# ---------------------------------------------------------------------------


def test_validate_scaffold_clean_exec_no_issues(tmp_path: Path) -> None:
    """validate_scaffold returns no issues after a successful execute_plan."""
    plan = plan_scaffold(tmp_path, profile="generic", template="standard")
    execute_plan(plan)
    issues = validate_scaffold(tmp_path, plan)
    assert issues == []


def test_validate_scaffold_missing_dir(tmp_path: Path) -> None:
    """validate_scaffold reports SCAFFOLD_DIR_MISSING for absent directories."""
    plan = plan_scaffold(tmp_path, profile="generic", template="standard")
    # Do NOT execute the plan — directories are absent
    issues = validate_scaffold(tmp_path, plan)
    codes = {i.code for i in issues}
    assert "SCAFFOLD_DIR_MISSING" in codes


def test_validate_scaffold_missing_file(tmp_path: Path) -> None:
    """validate_scaffold reports SCAFFOLD_FILE_MISSING for absent files."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    # Create directories but not files
    for d in plan.directories:
        d.mkdir(parents=True, exist_ok=True)
    issues = validate_scaffold(tmp_path, plan)
    codes = {i.code for i in issues}
    assert "SCAFFOLD_FILE_MISSING" in codes


def test_validate_scaffold_partial_exec(tmp_path: Path) -> None:
    """validate_scaffold catches missing files after partial execution."""
    plan = plan_scaffold(tmp_path, profile="generic", template="standard")
    execute_plan(plan)
    # Remove one file
    readme = tmp_path / "docs" / "governance" / "README.governance.md"
    readme.unlink()
    issues = validate_scaffold(tmp_path, plan)
    assert any(i.code == "SCAFFOLD_FILE_MISSING" for i in issues)


# ---------------------------------------------------------------------------
# format_plan — dry-run display
# ---------------------------------------------------------------------------


def test_format_plan_no_io(tmp_path: Path) -> None:
    """format_plan does not create any files or directories."""
    plan = plan_scaffold(tmp_path, profile="generic", template="standard")
    _ = format_plan(plan)
    # Nothing should exist after format_plan
    assert not (tmp_path / "governance.yaml").exists()


def test_format_plan_contains_profile_and_template(tmp_path: Path) -> None:
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    output = format_plan(plan)
    assert "generic" in output
    assert "minimal" in output


def test_format_plan_lists_files(tmp_path: Path) -> None:
    """format_plan output mentions the planned files."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    output = format_plan(plan)
    # governance.yaml and the example pipeline should appear
    assert "governance.yaml" in output
    assert "001--example.md" in output


def test_format_plan_check_existing_marks_new(tmp_path: Path) -> None:
    """With check_existing=True, new files are marked with '+' prefix."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    output = format_plan(plan, check_existing=True)
    assert "+" in output


def test_format_plan_check_existing_marks_existing(tmp_path: Path) -> None:
    """With check_existing=True, pre-existing files are marked."""
    plan = plan_scaffold(tmp_path, profile="generic", template="minimal")
    # Pre-create one file
    gov_yaml = tmp_path / "governance.yaml"
    gov_yaml.parent.mkdir(parents=True, exist_ok=True)
    gov_yaml.write_text("# existing", encoding="utf-8")

    output = format_plan(plan, check_existing=True)
    assert "exists" in output.lower() or "skip" in output.lower()


# ---------------------------------------------------------------------------
# Multi-agent scaffold (codex:multi-agent)
# ---------------------------------------------------------------------------


def test_multi_agent_scaffold_roles(tmp_path: Path) -> None:
    """codex:multi-agent plan includes role definition files."""
    plan = plan_scaffold(tmp_path, profile="codex", template="multi-agent")
    paths = {sf.path for sf in plan.files}
    assert tmp_path / ".codex" / "agents" / "planner.toml" in paths
    assert tmp_path / ".codex" / "agents" / "implementer.toml" in paths
    assert tmp_path / ".codex" / "agents" / "reviewer.toml" in paths


def test_multi_agent_scaffold_role_contracts(tmp_path: Path) -> None:
    """codex:multi-agent plan includes role governance contracts."""
    plan = plan_scaffold(tmp_path, profile="codex", template="multi-agent")
    paths = {sf.path for sf in plan.files}
    assert tmp_path / "docs" / "governance" / "agents" / "planner.md" in paths
    assert tmp_path / "docs" / "governance" / "agents" / "implementer.md" in paths
    assert tmp_path / "docs" / "governance" / "agents" / "reviewer.md" in paths


def test_multi_agent_scaffold_workflow_contract(tmp_path: Path) -> None:
    """codex:multi-agent plan includes the workflow contract."""
    plan = plan_scaffold(tmp_path, profile="codex", template="multi-agent")
    paths = {sf.path for sf in plan.files}
    assert tmp_path / "docs" / "contracts" / "multi-agent-workflow.md" in paths


def test_multi_agent_scaffold_artifact_dirs(tmp_path: Path) -> None:
    """codex:multi-agent plan includes handoffs and reviews directories."""
    plan = plan_scaffold(tmp_path, profile="codex", template="multi-agent")
    assert tmp_path / "artifacts" / "governance" / "handoffs" in plan.directories
    assert tmp_path / "artifacts" / "governance" / "reviews" in plan.directories


def test_multi_agent_execute_creates_all_structures(tmp_path: Path) -> None:
    """Executing a codex:multi-agent plan creates all expected structures."""
    plan = plan_scaffold(tmp_path, profile="codex", template="multi-agent")
    execute_plan(plan)
    assert (tmp_path / ".codex" / "agents" / "planner.toml").exists()
    assert (tmp_path / "docs" / "governance" / "agents" / "reviewer.md").exists()
    assert (tmp_path / "docs" / "contracts" / "multi-agent-workflow.md").exists()
    assert (tmp_path / "artifacts" / "governance" / "handoffs").is_dir()
    assert (tmp_path / "artifacts" / "governance" / "reviews").is_dir()


def test_multi_agent_validate_clean(tmp_path: Path) -> None:
    """validate_scaffold reports no issues after full multi-agent execution."""
    plan = plan_scaffold(tmp_path, profile="codex", template="multi-agent")
    execute_plan(plan)
    issues = validate_scaffold(tmp_path, plan)
    assert issues == []
