"""Tests for extended init levels and profiles."""



from governance_os.scaffolding.init import format_result, init_repo, validate_doctrine


def test_init_minimal_creates_minimal_structure(tmp_path):
    result = init_repo(tmp_path, level="minimal")
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "governance.yaml").exists()
    # docs/governance should NOT exist for minimal
    assert not (tmp_path / "docs" / "governance").exists()
    assert result.level == "minimal"


def test_init_standard_creates_full_structure(tmp_path):
    result = init_repo(tmp_path, level="standard")
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "docs" / "governance").is_dir()
    assert (tmp_path / "governance.yaml").exists()
    assert result.level == "standard"


def test_init_governed_creates_extended_structure(tmp_path):
    result = init_repo(tmp_path, level="governed")
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "governance" / "skills").is_dir()
    assert (tmp_path / "artifacts" / "governance").is_dir()
    # Governed level creates doctrine
    assert (tmp_path / "governance" / "doctrine" / "doctrine.md").exists()
    assert result.level == "governed"


def test_init_with_doctrine_flag(tmp_path):
    init_repo(tmp_path, level="standard", with_doctrine=True)
    assert (tmp_path / "governance" / "doctrine" / "doctrine.md").exists()


def test_init_codex_profile_creates_sessions(tmp_path):
    result = init_repo(tmp_path, level="standard", profile="codex")
    assert (tmp_path / "governance" / "sessions" / "session-template.md").exists()
    assert result.profile == "codex"


def test_init_generic_profile_no_sessions(tmp_path):
    result = init_repo(tmp_path, level="standard", profile="generic")
    assert not (tmp_path / "governance" / "sessions").exists()
    assert result.profile == "generic"


def test_init_invalid_level_falls_back_to_standard(tmp_path):
    init_repo(tmp_path, level="nonexistent")
    # Should fall back to standard and not raise
    assert (tmp_path / "docs" / "governance").is_dir()


def test_init_idempotent_with_level(tmp_path):
    init_repo(tmp_path, level="standard")
    result = init_repo(tmp_path, level="standard")
    # Files should be skipped on second run
    assert len(result.skipped_files) > 0


def test_format_result_includes_level_profile(tmp_path):
    result = init_repo(tmp_path, level="governed", profile="codex")
    output = format_result(result)
    assert "governed" in output
    assert "codex" in output


def test_validate_doctrine_missing(tmp_path):
    issues = validate_doctrine(tmp_path)
    assert len(issues) == 1
    assert "not found" in issues[0]


def test_validate_doctrine_present(tmp_path):
    doctrine_path = tmp_path / "governance" / "doctrine" / "doctrine.md"
    doctrine_path.parent.mkdir(parents=True)
    doctrine_path.write_text("# Doctrine\n\nPrinciples:\n1. Do good.\n", encoding="utf-8")
    issues = validate_doctrine(tmp_path)
    assert not issues


def test_validate_doctrine_empty(tmp_path):
    doctrine_path = tmp_path / "governance" / "doctrine" / "doctrine.md"
    doctrine_path.parent.mkdir(parents=True)
    doctrine_path.write_text("", encoding="utf-8")
    issues = validate_doctrine(tmp_path)
    assert any("empty" in i for i in issues)
