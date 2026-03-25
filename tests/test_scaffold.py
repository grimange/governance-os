"""Tests for governance_os.scaffolding.init."""

from pathlib import Path

from governance_os.scaffolding.init import format_result, init_repo


def test_init_creates_directories(tmp_path: Path) -> None:
    """init_repo creates the standard governance directory layout."""
    result = init_repo(tmp_path)
    assert (tmp_path / "governance" / "pipelines").is_dir()
    assert (tmp_path / "docs" / "governance").is_dir()
    assert (tmp_path / "artifacts").is_dir()
    assert tmp_path / "governance" / "pipelines" in result.created_dirs
    assert tmp_path / "docs" / "governance" in result.created_dirs
    assert tmp_path / "artifacts" in result.created_dirs


def test_init_creates_files(tmp_path: Path) -> None:
    """init_repo creates governance.yaml and starter files."""
    result = init_repo(tmp_path)
    assert (tmp_path / "governance.yaml").exists()
    assert (tmp_path / "governance" / "pipelines" / "001--example.md").exists()
    assert (tmp_path / "docs" / "governance" / "README.governance.md").exists()
    assert tmp_path / "governance.yaml" in result.created_files


def test_init_skips_existing_files(tmp_path: Path) -> None:
    """init_repo skips files that already exist."""
    existing = tmp_path / "governance.yaml"
    existing.write_text("# my config", encoding="utf-8")

    result = init_repo(tmp_path)

    assert existing in result.skipped_files
    assert existing not in result.created_files
    assert existing.read_text(encoding="utf-8") == "# my config"


def test_init_idempotent(tmp_path: Path) -> None:
    """Running init_repo twice does not fail and skips existing artefacts."""
    init_repo(tmp_path)
    result2 = init_repo(tmp_path)
    assert not result2.created_dirs
    assert not result2.created_files
    assert result2.skipped_files


def test_init_creates_target_dir(tmp_path: Path) -> None:
    """init_repo creates the root directory if it does not exist."""
    new_root = tmp_path / "new-repo"
    init_repo(new_root)
    assert new_root.is_dir()


def test_format_result_contains_root(tmp_path: Path) -> None:
    """format_result output mentions the root path."""
    result = init_repo(tmp_path)
    output = format_result(result)
    assert str(tmp_path) in output


def test_format_result_skipped(tmp_path: Path) -> None:
    """format_result lists skipped files when present."""
    init_repo(tmp_path)
    result2 = init_repo(tmp_path)
    output = format_result(result2)
    assert "skipped" in output.lower()


def test_governance_yaml_content(tmp_path: Path) -> None:
    """Created governance.yaml contains expected keys."""
    init_repo(tmp_path)
    content = (tmp_path / "governance.yaml").read_text(encoding="utf-8")
    assert "pipelines_dir" in content
    assert "contracts_glob" in content


def test_example_pipeline_content(tmp_path: Path) -> None:
    """Created example pipeline is valid markdown with required sections."""
    init_repo(tmp_path)
    content = (tmp_path / "governance" / "pipelines" / "001--example.md").read_text(
        encoding="utf-8"
    )
    assert content.startswith("# ")
    assert "Stage:" in content
    assert "Depends on:" in content
