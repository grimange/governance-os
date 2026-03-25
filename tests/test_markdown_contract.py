"""Tests for governance_os.parsing.markdown_contract."""

from pathlib import Path

from governance_os.parsing.markdown_contract import ParsedContract, parse_contract

_FULL_CONTRACT = """\
# 001 — Full Example

Stage: establish

Purpose:
Does the thing.

Depends on:
- none

Inputs:
- some input

Outputs:
- artifacts/output.json

Implementation Notes:
Keep it simple.

Success Criteria:
- criteria met

Out of Scope:
- nothing yet
"""

_HEADING_STYLE = """\
# 002 — Heading Style

### Stage
implement

### Purpose
Uses headings.

### Depends on
- 001

### Outputs
- artifacts/result.md

### Success Criteria
- works
"""


def _parse(src: str, name: str = "001--test.md") -> ParsedContract:
    return parse_contract(Path(name), source=src)


def test_parses_title():
    c = _parse(_FULL_CONTRACT)
    assert c.title == "001 — Full Example"


def test_parses_stage():
    c = _parse(_FULL_CONTRACT)
    assert c.stage == "establish"


def test_parses_purpose():
    c = _parse(_FULL_CONTRACT)
    assert "Does the thing" in c.purpose


def test_parses_depends_on():
    c = _parse(_FULL_CONTRACT)
    assert "none" in c.depends_on


def test_parses_inputs():
    c = _parse(_FULL_CONTRACT)
    assert "some input" in c.inputs


def test_parses_outputs():
    c = _parse(_FULL_CONTRACT)
    assert "artifacts/output.json" in c.outputs


def test_parses_implementation_notes():
    c = _parse(_FULL_CONTRACT)
    assert "simple" in c.implementation_notes.lower()


def test_parses_success_criteria():
    c = _parse(_FULL_CONTRACT)
    assert "criteria met" in c.success_criteria


def test_parses_out_of_scope():
    c = _parse(_FULL_CONTRACT)
    assert "nothing yet" in c.out_of_scope


def test_no_issues_for_valid_contract():
    c = _parse(_FULL_CONTRACT)
    assert c.issues == []


def test_heading_style_stage():
    c = _parse(_HEADING_STYLE, "002--heading.md")
    assert c.stage == "implement"


def test_heading_style_depends_on():
    c = _parse(_HEADING_STYLE, "002--heading.md")
    assert "001" in c.depends_on


def test_heading_style_outputs():
    c = _parse(_HEADING_STYLE, "002--heading.md")
    assert "artifacts/result.md" in c.outputs


def test_missing_title_reported():
    src = "Stage: establish\n\nPurpose:\nFoo.\n\nOutputs:\n- x\n\nSuccess Criteria:\n- y\n"
    c = _parse(src)
    codes = [i.code for i in c.issues]
    assert "MISSING_TITLE" in codes


def test_missing_stage_reported():
    src = "# Title\n\nPurpose:\nFoo.\n\nOutputs:\n- x\n\nSuccess Criteria:\n- y\n"
    c = _parse(src)
    codes = [i.code for i in c.issues]
    assert "MISSING_STAGE" in codes


def test_missing_outputs_reported():
    src = "# Title\n\nStage: establish\n\nPurpose:\nFoo.\n\nSuccess Criteria:\n- y\n"
    c = _parse(src)
    codes = [i.code for i in c.issues]
    assert "MISSING_OUTPUTS" in codes


def test_missing_success_criteria_reported():
    src = "# Title\n\nStage: establish\n\nPurpose:\nFoo.\n\nOutputs:\n- x\n"
    c = _parse(src)
    codes = [i.code for i in c.issues]
    assert "MISSING_SUCCESS_CRITERIA" in codes


def test_parse_issue_has_path():
    c = _parse("# Title\n", "001--x.md")
    for issue in c.issues:
        assert issue.path == Path("001--x.md")


def test_reads_from_file(tmp_path):
    f = tmp_path / "001--file.md"
    f.write_text(_FULL_CONTRACT, encoding="utf-8")
    c = parse_contract(f)
    assert c.title == "001 — Full Example"
    assert c.stage == "establish"
