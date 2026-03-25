"""Tests for governance_os.config."""

import textwrap
from pathlib import Path

import pytest
from pydantic import ValidationError

from governance_os.config import GovernanceConfig, load_config, resolve_pipelines_dir


def test_load_config_defaults(tmp_path: Path) -> None:
    """load_config returns defaults when governance.yaml is absent."""
    cfg = load_config(tmp_path)
    assert cfg.pipelines_dir == "pipelines"
    assert cfg.contracts_glob == "**/*.md"


def test_load_config_from_file(tmp_path: Path) -> None:
    """load_config reads values from governance.yaml."""
    (tmp_path / "governance.yaml").write_text(
        textwrap.dedent("""\
            pipelines_dir: contracts
            contracts_glob: "*.md"
        """),
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.pipelines_dir == "contracts"
    assert cfg.contracts_glob == "*.md"


def test_load_config_empty_file(tmp_path: Path) -> None:
    """load_config handles an empty governance.yaml gracefully."""
    (tmp_path / "governance.yaml").write_text("", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.pipelines_dir == "pipelines"


def test_load_config_invalid_pipelines_dir(tmp_path: Path) -> None:
    """load_config raises when pipelines_dir is blank."""
    (tmp_path / "governance.yaml").write_text("pipelines_dir: '   '", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(tmp_path)


def test_resolve_pipelines_dir(tmp_path: Path) -> None:
    """resolve_pipelines_dir returns root / pipelines_dir."""
    cfg = GovernanceConfig(pipelines_dir="my_pipes")
    result = resolve_pipelines_dir(tmp_path, cfg)
    assert result == tmp_path / "my_pipes"
