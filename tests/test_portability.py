"""Tests for governance_os.validation.portability."""

from pathlib import Path

import pytest

from governance_os.models.issue import Severity
from governance_os.models.pipeline import Pipeline
from governance_os.validation.portability import scan_pipeline, scan_pipelines


def _p(outputs):
    return Pipeline(numeric_id="001", slug="x", path=Path("001--x.md"), outputs=outputs)


def test_clean_relative_path_no_issues():
    assert scan_pipeline(_p(["artifacts/report.json"])) == []


def test_multiple_clean_paths_no_issues():
    assert scan_pipeline(_p(["artifacts/a.json", "docs/b.md"])) == []


def test_empty_outputs_no_issues():
    assert scan_pipeline(_p([])) == []


def test_unix_absolute_path():
    issues = scan_pipeline(_p(["/etc/passwd"]))
    assert any(i.code == "ABSOLUTE_PATH" for i in issues)


def test_unix_absolute_path_is_error():
    issues = scan_pipeline(_p(["/bad/path"]))
    assert all(i.severity == Severity.ERROR for i in issues)


@pytest.mark.parametrize("path", ["C:/Users/foo", "D:/out.txt", "z:/data"])
def test_windows_drive_path(path):
    issues = scan_pipeline(_p([path]))
    assert any(i.code == "WINDOWS_DRIVE_PATH" for i in issues)


@pytest.mark.parametrize("path", ["../escape", "../../root", "a/../../../b"])
def test_path_traversal(path):
    issues = scan_pipeline(_p([path]))
    assert any(i.code == "PATH_TRAVERSAL" for i in issues)


def test_home_tilde_path():
    issues = scan_pipeline(_p(["~/output.md"]))
    assert any(i.code == "HOME_RELATIVE_PATH" for i in issues)


def test_mixed_outputs_only_bad_flagged():
    issues = scan_pipeline(_p(["artifacts/ok.json", "/bad/path"]))
    assert len(issues) == 1
    assert issues[0].code == "ABSOLUTE_PATH"


def test_scan_pipelines_aggregates():
    pipelines = [
        Pipeline(numeric_id="001", slug="a", path=Path("001--a.md"), outputs=["ok/path"]),
        Pipeline(numeric_id="002", slug="b", path=Path("002--b.md"), outputs=["/bad"]),
        Pipeline(numeric_id="003", slug="c", path=Path("003--c.md"), outputs=["C:/win"]),
    ]
    issues = scan_pipelines(pipelines)
    assert len(issues) == 2


def test_issue_includes_pipeline_id():
    issues = scan_pipeline(_p(["/bad"]))
    assert issues[0].pipeline_id == "001"


def test_issue_includes_path():
    issues = scan_pipeline(_p(["/bad"]))
    assert issues[0].path == Path("001--x.md")
