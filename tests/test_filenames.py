"""Tests for governance_os.parsing.filenames."""

from pathlib import Path

import pytest

from governance_os.parsing.filenames import (
    FilenameParseError,
    PipelineIdentity,
    parse_filename,
    parse_filenames,
)


@pytest.mark.parametrize("name,expected_id,expected_slug", [
    ("001--setup.md", "001", "setup"),
    ("042--verify-outputs.md", "042", "verify-outputs"),
    ("999--release-v1.md", "999", "release-v1"),
    ("001--a.md", "001", "a"),
    ("0001--long-id.md", "0001", "long-id"),
])
def test_valid_filenames(name, expected_id, expected_slug):
    result = parse_filename(Path(name))
    assert isinstance(result, PipelineIdentity)
    assert result.numeric_id == expected_id
    assert result.slug == expected_slug


@pytest.mark.parametrize("name", [
    "001-single-dash.md",    # single dash
    "example.md",            # no id
    "001--Example.md",       # uppercase slug
    "001--.md",              # empty slug
    "001--foo.txt",          # wrong extension
    "--foo.md",              # no numeric id
    "abc--foo.md",           # non-numeric id
    "001--foo bar.md",       # space in slug
])
def test_invalid_filenames(name):
    result = parse_filename(Path(name))
    assert isinstance(result, FilenameParseError)
    assert result.path == Path(name)
    assert result.reason


def test_parse_filename_preserves_path():
    p = Path("some/dir/001--foo.md")
    result = parse_filename(p)
    assert isinstance(result, PipelineIdentity)
    assert result.path == p


def test_parse_filenames_splits_valid_and_invalid():
    paths = [
        Path("001--alpha.md"),
        Path("bad-name.md"),
        Path("002--beta.md"),
        Path("003-gamma.md"),
    ]
    ids, errors = parse_filenames(paths)
    assert len(ids) == 2
    assert len(errors) == 2
    assert {i.numeric_id for i in ids} == {"001", "002"}


def test_parse_filenames_all_valid():
    paths = [Path(f"00{i}--item.md") for i in range(1, 4)]
    ids, errors = parse_filenames(paths)
    assert len(ids) == 3
    assert errors == []


def test_parse_filenames_all_invalid():
    paths = [Path("bad.md"), Path("also-bad.txt")]
    ids, errors = parse_filenames(paths)
    assert ids == []
    assert len(errors) == 2


def test_parse_filenames_empty():
    ids, errors = parse_filenames([])
    assert ids == []
    assert errors == []
