"""Tests for governance_os.discovery."""

from pathlib import Path

import pytest

from governance_os.config import GovernanceConfig
from governance_os.discovery import DiscoveryResult, discover, format_result


def _make_contract(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_text(f"# {name}\n", encoding="utf-8")
    return path


def test_discover_finds_markdown_files(tmp_path: Path) -> None:
    """discover returns all .md files in pipelines_dir."""
    pipes = tmp_path / "pipelines"
    pipes.mkdir()
    _make_contract(pipes, "001-alpha.md")
    _make_contract(pipes, "002-beta.md")

    result = discover(tmp_path)

    assert len(result.contracts) == 2
    assert not result.missing_dir


def test_discover_sorted_by_name(tmp_path: Path) -> None:
    """discover returns contracts sorted by filename."""
    pipes = tmp_path / "pipelines"
    pipes.mkdir()
    _make_contract(pipes, "003-gamma.md")
    _make_contract(pipes, "001-alpha.md")
    _make_contract(pipes, "002-beta.md")

    result = discover(tmp_path)

    names = [p.name for p in result.contracts]
    assert names == sorted(names)


def test_discover_missing_dir(tmp_path: Path) -> None:
    """discover sets missing_dir=True when pipelines_dir does not exist."""
    result = discover(tmp_path)
    assert result.missing_dir
    assert result.contracts == []


def test_discover_empty_dir(tmp_path: Path) -> None:
    """discover returns empty list when pipelines_dir has no .md files."""
    (tmp_path / "pipelines").mkdir()
    result = discover(tmp_path)
    assert result.contracts == []
    assert not result.missing_dir


def test_discover_ignores_non_markdown(tmp_path: Path) -> None:
    """discover ignores non-.md files."""
    pipes = tmp_path / "pipelines"
    pipes.mkdir()
    (pipes / "notes.txt").write_text("ignore me", encoding="utf-8")
    _make_contract(pipes, "001-real.md")

    result = discover(tmp_path)

    assert len(result.contracts) == 1
    assert result.contracts[0].name == "001-real.md"


def test_discover_custom_config(tmp_path: Path) -> None:
    """discover respects a custom pipelines_dir from config."""
    custom = tmp_path / "contracts"
    custom.mkdir()
    _make_contract(custom, "001-x.md")

    config = GovernanceConfig(pipelines_dir="contracts")
    result = discover(tmp_path, config=config)

    assert len(result.contracts) == 1


def test_discover_subdirectory_glob(tmp_path: Path) -> None:
    """discover finds contracts in subdirectories with default glob."""
    pipes = tmp_path / "pipelines"
    sub = pipes / "stage-1"
    sub.mkdir(parents=True)
    _make_contract(sub, "001-nested.md")

    result = discover(tmp_path)

    assert len(result.contracts) == 1
    assert result.contracts[0].name == "001-nested.md"


def test_format_result_missing_dir(tmp_path: Path) -> None:
    """format_result mentions missing dir and init suggestion."""
    result = DiscoveryResult(pipelines_dir=tmp_path / "pipelines", missing_dir=True)
    output = format_result(result, tmp_path)
    assert "not found" in output.lower()
    assert "govos init" in output


def test_format_result_no_contracts(tmp_path: Path) -> None:
    """format_result reports no contracts found."""
    (tmp_path / "pipelines").mkdir()
    result = discover(tmp_path)
    output = format_result(result, tmp_path)
    assert "no contracts" in output.lower()


def test_format_result_lists_contracts(tmp_path: Path) -> None:
    """format_result lists each contract path."""
    pipes = tmp_path / "pipelines"
    pipes.mkdir()
    _make_contract(pipes, "001-alpha.md")
    _make_contract(pipes, "002-beta.md")

    result = discover(tmp_path)
    output = format_result(result, tmp_path)

    assert "001-alpha.md" in output
    assert "002-beta.md" in output
    assert "2 contract" in output
