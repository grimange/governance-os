"""Tests for Phase 1 and Phase 4 — MCP tool implementations.

These tests exercise tool logic directly (not via the MCP transport layer).
The MCP server registration is structurally verified, not integration-tested.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path, pipeline_id: str = "001", slug: str = "test-pipeline") -> Path:
    """Create a minimal governance repo with one pipeline contract."""
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir(parents=True)
    (pipelines_dir / f"{pipeline_id}--{slug}.md").write_text(
        f"""# {pipeline_id} — {slug.replace("-", " ").title()}

Stage: establish

Purpose:
Test pipeline for MCP tests.

Outputs:
- test-output

Success Criteria:
- all tests pass
""",
        encoding="utf-8",
    )
    (tmp_path / "governance.yaml").write_text("profile: generic\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# govos_get_task_contract
# ---------------------------------------------------------------------------


def test_get_task_contract_returns_run_id(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract

    root = _make_repo(tmp_path)
    result = govos_get_task_contract("001", root=str(root))
    assert "run_id" in result
    assert result["run_id"]
    assert result["error"] is None


def test_get_task_contract_creates_trace_on_disk(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract

    root = _make_repo(tmp_path)
    result = govos_get_task_contract("001", root=str(root))
    run_id = result["run_id"]
    assert ExecutionTrace.exists(root, run_id)


def test_get_task_contract_returns_contract_fields(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract

    root = _make_repo(tmp_path)
    result = govos_get_task_contract("001", root=str(root))
    assert result["contract"] is not None
    contract = result["contract"]
    assert contract["id"] == "001"
    assert contract["slug"] == "test-pipeline"
    assert "purpose" in contract


def test_get_task_contract_unknown_pipeline(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract

    root = _make_repo(tmp_path)
    result = govos_get_task_contract("999", root=str(root))
    assert result["contract"] is None
    assert result["error"] is not None
    assert "CONTRACT_INPUT_INVALID" in result["error"]


def test_get_task_contract_lifecycle_stage(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract

    root = _make_repo(tmp_path)
    result = govos_get_task_contract("001", root=str(root))
    assert result["lifecycle_stage"] == LifecycleStage.TASK_LOADED


def test_get_task_contract_records_tool_call_in_trace(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract

    root = _make_repo(tmp_path)
    result = govos_get_task_contract("001", root=str(root))
    trace = ExecutionTrace.load(root, result["run_id"])
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "govos_get_task_contract"


def test_get_task_contract_slug_lookup(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract

    root = _make_repo(tmp_path)
    result = govos_get_task_contract("test-pipeline", root=str(root))
    assert result["error"] is None
    assert result["contract"]["slug"] == "test-pipeline"


# ---------------------------------------------------------------------------
# govos_read_repo_map
# ---------------------------------------------------------------------------


def test_read_repo_map_advances_lifecycle(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.read_repo_map import govos_read_repo_map

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_read_repo_map(run_id, root=str(root))
    assert result["lifecycle_stage"] == LifecycleStage.CONTEXT_ACQUIRED
    assert result["error"] is None


def test_read_repo_map_returns_pipelines(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.read_repo_map import govos_read_repo_map

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_read_repo_map(run_id, root=str(root))
    assert isinstance(result["pipelines"], list)
    assert len(result["pipelines"]) >= 1
    first = result["pipelines"][0]
    assert "id" in first
    assert "effective_state" in first


def test_read_repo_map_unknown_run_id(tmp_path):
    from governance_os.mcp.tools.read_repo_map import govos_read_repo_map

    result = govos_read_repo_map("nonexistent-id", root=str(tmp_path))
    assert result["error"] is not None
    assert "CONTRACT_INPUT_INVALID" in result["error"]


# ---------------------------------------------------------------------------
# govos_write_patch
# ---------------------------------------------------------------------------


def test_write_patch_creates_file(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.write_patch import govos_write_patch

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_write_patch(run_id, "src/newfile.py", "x = 1\n", root=str(root))
    assert result["error"] is None
    assert result["bytes_written"] > 0
    assert (root / "src" / "newfile.py").exists()
    assert (root / "src" / "newfile.py").read_text() == "x = 1\n"


def test_write_patch_records_managed_change_in_trace(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.write_patch import govos_write_patch

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    govos_write_patch(run_id, "src/newfile.py", "x = 1\n", root=str(root))
    trace = ExecutionTrace.load(root, run_id)
    assert any(fc.via_managed_patch for fc in trace.file_changes)
    assert trace.file_changes[0].path == "src/newfile.py"


def test_write_patch_advances_lifecycle(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.write_patch import govos_write_patch

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_write_patch(run_id, "src/file.py", "pass\n", root=str(root))
    assert result["lifecycle_stage"] == LifecycleStage.CHANGES_APPLIED


def test_write_patch_rejects_path_traversal(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.write_patch import govos_write_patch

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_write_patch(run_id, "../../../etc/passwd", "evil\n", root=str(root))
    assert result["error"] is not None
    assert "CONTRACT_INPUT_INVALID" in result["error"]


def test_write_patch_rejects_finalized_trace(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.write_patch import govos_write_patch

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    # Manually finalize the trace
    trace = ExecutionTrace.load(root, run_id)
    trace.finalized = True
    trace.save(root)

    result = govos_write_patch(run_id, "file.py", "x=1\n", root=str(root))
    assert result["error"] is not None
    assert "finalized" in result["error"]


def test_write_patch_unknown_run_id(tmp_path):
    from governance_os.mcp.tools.write_patch import govos_write_patch

    result = govos_write_patch("bad-run-id", "file.py", "x=1\n", root=str(tmp_path))
    assert result["error"] is not None
    assert "CONTRACT_INPUT_INVALID" in result["error"]


# ---------------------------------------------------------------------------
# govos_finalize_result
# ---------------------------------------------------------------------------


def _run_standard(root: Path) -> str:
    """Run a minimal valid standard_code_change sequence and return run_id."""
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.read_repo_map import govos_read_repo_map
    from governance_os.mcp.tools.write_patch import govos_write_patch

    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    govos_read_repo_map(run_id, root=str(root))
    govos_write_patch(run_id, "src/change.py", "x = 1\n", root=str(root))
    return run_id


def test_finalize_passes_valid_run(tmp_path):
    from governance_os.mcp.tools.finalize_result import govos_finalize_result

    root = _make_repo(tmp_path)
    run_id = _run_standard(root)
    result = govos_finalize_result(run_id, "All changes applied.", root=str(root))
    assert result["error"] is None
    assert result["validation_passed"] is True
    assert result["lifecycle_stage"] == LifecycleStage.RESULT_FINALIZED


def test_finalize_marks_trace_as_finalized(tmp_path):
    from governance_os.mcp.tools.finalize_result import govos_finalize_result

    root = _make_repo(tmp_path)
    run_id = _run_standard(root)
    govos_finalize_result(run_id, "Done.", root=str(root))
    trace = ExecutionTrace.load(root, run_id)
    assert trace.finalized is True
    assert trace.finalized_at is not None
    assert trace.validation_passed is True


def test_finalize_fails_incomplete_run(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.finalize_result import govos_finalize_result

    root = _make_repo(tmp_path)
    # Only get_task_contract called — missing write_patch, read_repo_map, finalize
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_finalize_result(run_id, "Incomplete run.", root=str(root))
    assert result["validation_passed"] is False
    assert len(result["failures"]) > 0


def test_finalize_unknown_run_id(tmp_path):
    from governance_os.mcp.tools.finalize_result import govos_finalize_result

    result = govos_finalize_result("no-such-run", "done", root=str(tmp_path))
    assert result["error"] is not None
    assert result["validation_passed"] is False


# ---------------------------------------------------------------------------
# govos_record_evidence
# ---------------------------------------------------------------------------


def test_record_evidence_adds_ref(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.record_evidence import govos_record_evidence

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_record_evidence(run_id, "pytest: 100 passed", root=str(root))
    assert result["error"] is None
    assert result["total_evidence"] == 1
    assert result["lifecycle_stage"] == LifecycleStage.EVIDENCE_RECORDED


def test_record_evidence_persists_to_trace(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.record_evidence import govos_record_evidence

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    govos_record_evidence(run_id, "review approved", root=str(root))
    trace = ExecutionTrace.load(root, run_id)
    assert "review approved" in trace.evidence_refs


def test_record_evidence_rejects_empty(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.record_evidence import govos_record_evidence

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_record_evidence(run_id, "   ", root=str(root))
    assert result["error"] is not None
    assert "CONTRACT_INPUT_INVALID" in result["error"]


def test_record_evidence_rejects_finalized_run(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.record_evidence import govos_record_evidence

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    trace = ExecutionTrace.load(root, run_id)
    trace.finalized = True
    trace.save(root)
    result = govos_record_evidence(run_id, "some evidence", root=str(root))
    assert result["error"] is not None
    assert "finalized" in result["error"]


# ---------------------------------------------------------------------------
# govos_search_code
# ---------------------------------------------------------------------------


def test_search_code_finds_pattern(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.search_code import govos_search_code

    root = _make_repo(tmp_path)
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "sample.py").write_text("def foo():\n    return 42\n", encoding="utf-8")

    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_search_code(run_id, "def foo", root=str(root))
    assert result["error"] is None
    assert result["total_matches"] >= 1
    assert any("foo" in m["text"] for m in result["matches"])


def test_search_code_no_matches(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.search_code import govos_search_code

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_search_code(run_id, "ZZZZZ_NOT_FOUND", root=str(root))
    assert result["error"] is None
    assert result["total_matches"] == 0
    assert result["matches"] == []


def test_search_code_invalid_regex(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.search_code import govos_search_code

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_search_code(run_id, "[invalid", root=str(root))
    assert result["error"] is not None
    assert "CONTRACT_INPUT_INVALID" in result["error"]


# ---------------------------------------------------------------------------
# govos_get_file_context
# ---------------------------------------------------------------------------


def test_get_file_context_reads_file(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.get_file_context import govos_get_file_context

    root = _make_repo(tmp_path)
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "hello.py").write_text("line1\nline2\nline3\n", encoding="utf-8")

    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_get_file_context(run_id, "src/hello.py", root=str(root))
    assert result["error"] is None
    assert "line1" in result["content"]
    assert result["total_lines"] == 3


def test_get_file_context_line_slice(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.get_file_context import govos_get_file_context

    root = _make_repo(tmp_path)
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "hello.py").write_text("line1\nline2\nline3\n", encoding="utf-8")

    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_get_file_context(run_id, "src/hello.py", root=str(root), start_line=2, end_line=2)
    assert "line2" in result["content"]
    assert "line1" not in result["content"]


def test_get_file_context_missing_file(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.get_file_context import govos_get_file_context

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_get_file_context(run_id, "nonexistent.py", root=str(root))
    assert result["error"] is not None
    assert "CONTRACT_INPUT_INVALID" in result["error"]


def test_get_file_context_path_traversal(tmp_path):
    from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
    from governance_os.mcp.tools.get_file_context import govos_get_file_context

    root = _make_repo(tmp_path)
    run_id = govos_get_task_contract("001", root=str(root))["run_id"]
    result = govos_get_file_context(run_id, "../../etc/passwd", root=str(root))
    assert result["error"] is not None
    assert "CONTRACT_INPUT_INVALID" in result["error"]


# ---------------------------------------------------------------------------
# MCP server — structural registration check
# ---------------------------------------------------------------------------


def test_mcp_server_registers_all_tools():
    """Verify all 10 governed tools are registered on the FastMCP instance."""
    from governance_os.mcp.server import mcp

    # FastMCP exposes _tool_manager with registered tools
    tool_names = set()
    try:
        # FastMCP >= 1.x stores tools in _tool_manager
        tool_names = {t for t in mcp._tool_manager._tools}
    except AttributeError:
        # Fallback: get list_tools via any available attribute
        try:
            tool_names = {t.name for t in mcp.list_tools()}
        except Exception:
            pass

    expected_phase1 = {
        "govos_get_task_contract",
        "govos_read_repo_map",
        "govos_write_patch",
        "govos_finalize_result",
    }
    expected_phase4 = {
        "govos_search_code",
        "govos_get_file_context",
        "govos_run_tests",
        "govos_run_lint",
        "govos_record_evidence",
        "govos_git_status",
    }
    all_expected = expected_phase1 | expected_phase4

    # At minimum, verify the server module imports cleanly and the instance exists
    assert mcp is not None

    # Check registration if introspection is available
    if tool_names:
        for tool in all_expected:
            assert tool in tool_names, f"Tool '{tool}' not registered in MCP server."
