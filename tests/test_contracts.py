"""Tests for Phase 0 — contract foundation: tool_policy, failure_codes, execution_trace."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from governance_os.contracts.failure_codes import FailureCode
from governance_os.contracts.tool_policy import (
    HIGH_ASSURANCE_RELEASE,
    POLICY_REGISTRY,
    READ_ONLY_AUDIT,
    STANDARD_CODE_CHANGE,
    ToolPolicy,
)
from governance_os.contracts.execution_trace import (
    ExecutionTrace,
    FileChangeRecord,
    LifecycleStage,
    LIFECYCLE_ORDER,
    ToolCallRecord,
)


# ---------------------------------------------------------------------------
# FailureCode
# ---------------------------------------------------------------------------


def test_failure_codes_all_present():
    codes = {c.value for c in FailureCode}
    assert "TOOLING_UNAVAILABLE_FAIL_CLOSED" in codes
    assert "TOOL_POLICY_VIOLATION" in codes
    assert "TOOL_BYPASS_DETECTED" in codes
    assert "SEQUENCE_VIOLATION" in codes
    assert "EVIDENCE_MISSING" in codes
    assert "TEST_EXECUTION_MISSING" in codes
    assert "CONTRACT_INPUT_INVALID" in codes


def test_failure_codes_are_strings():
    for code in FailureCode:
        assert isinstance(code.value, str)
        assert code.value == code  # StrEnum comparison


# ---------------------------------------------------------------------------
# ToolPolicy model
# ---------------------------------------------------------------------------


def test_tool_policy_defaults():
    policy = ToolPolicy()
    assert policy.mode == "standard_code_change"
    assert policy.allowed_tools == []
    assert policy.required_tools == []
    assert policy.forbidden_command_classes == []
    assert policy.required_sequence == []
    assert policy.required_before_complete == []
    assert policy.completion_requirements == []


def test_tool_policy_is_frozen():
    policy = ToolPolicy()
    with pytest.raises(Exception):
        policy.mode = "changed"  # type: ignore[misc]


def test_tool_policy_custom_fields():
    policy = ToolPolicy(
        mode="custom",
        required_tools=["tool_a", "tool_b"],
        forbidden_command_classes=["unmanaged_write"],
    )
    assert "tool_a" in policy.required_tools
    assert "unmanaged_write" in policy.forbidden_command_classes


# ---------------------------------------------------------------------------
# Built-in policies
# ---------------------------------------------------------------------------


def test_read_only_audit_policy():
    assert READ_ONLY_AUDIT.mode == "read_only_audit"
    assert "govos_get_task_contract" in READ_ONLY_AUDIT.required_tools
    assert "govos_finalize_result" in READ_ONLY_AUDIT.required_tools
    assert "unmanaged_write" in READ_ONLY_AUDIT.forbidden_command_classes


def test_standard_code_change_policy():
    assert STANDARD_CODE_CHANGE.mode == "standard_code_change"
    assert "govos_write_patch" in STANDARD_CODE_CHANGE.required_tools
    assert "unmanaged_write" in STANDARD_CODE_CHANGE.forbidden_command_classes
    assert STANDARD_CODE_CHANGE.required_sequence[0] == "govos_get_task_contract"
    assert STANDARD_CODE_CHANGE.required_sequence[-1] == "govos_finalize_result"


def test_high_assurance_release_policy():
    assert HIGH_ASSURANCE_RELEASE.mode == "high_assurance_release"
    assert "govos_run_tests" in HIGH_ASSURANCE_RELEASE.required_tools
    assert "govos_record_evidence" in HIGH_ASSURANCE_RELEASE.required_tools
    assert "govos_finalize_result" in HIGH_ASSURANCE_RELEASE.required_tools


def test_policy_registry_contains_all_modes():
    assert "read_only_audit" in POLICY_REGISTRY
    assert "standard_code_change" in POLICY_REGISTRY
    assert "high_assurance_release" in POLICY_REGISTRY


def test_policy_registry_returns_correct_instances():
    assert POLICY_REGISTRY["read_only_audit"] is READ_ONLY_AUDIT
    assert POLICY_REGISTRY["standard_code_change"] is STANDARD_CODE_CHANGE


# ---------------------------------------------------------------------------
# ToolCallRecord
# ---------------------------------------------------------------------------


def test_tool_call_record_is_frozen():
    rec = ToolCallRecord(tool_name="test_tool", order=0)
    with pytest.raises(Exception):
        rec.tool_name = "other"  # type: ignore[misc]


def test_tool_call_record_defaults():
    rec = ToolCallRecord(tool_name="govos_get_task_contract", order=0)
    assert rec.result_ok is True
    assert rec.inputs == {}
    assert rec.order == 0


# ---------------------------------------------------------------------------
# FileChangeRecord
# ---------------------------------------------------------------------------


def test_file_change_record_is_frozen():
    rec = FileChangeRecord(path="foo.py", via_managed_patch=True)
    with pytest.raises(Exception):
        rec.path = "bar.py"  # type: ignore[misc]


def test_file_change_record_managed_patch_field():
    managed = FileChangeRecord(path="foo.py", via_managed_patch=True, patch_id="abc")
    unmanaged = FileChangeRecord(path="bar.py", via_managed_patch=False)
    assert managed.via_managed_patch is True
    assert unmanaged.via_managed_patch is False
    assert managed.patch_id == "abc"
    assert unmanaged.patch_id is None


# ---------------------------------------------------------------------------
# ExecutionTrace — basic fields
# ---------------------------------------------------------------------------


def test_execution_trace_auto_run_id():
    t1 = ExecutionTrace()
    t2 = ExecutionTrace()
    assert t1.run_id != t2.run_id
    assert len(t1.run_id) == 36  # UUID4


def test_execution_trace_defaults():
    trace = ExecutionTrace()
    assert trace.tool_calls == []
    assert trace.file_changes == []
    assert trace.evidence_refs == []
    assert trace.finalized is False
    assert trace.finalized_at is None
    assert trace.lifecycle_stage == LifecycleStage.TASK_LOADED
    assert trace.validation_passed is None


def test_execution_trace_record_tool_call():
    trace = ExecutionTrace()
    trace.record_tool_call("govos_get_task_contract", inputs={"pipeline_id": "001"})
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "govos_get_task_contract"
    assert trace.tool_calls[0].order == 0
    assert trace.tool_calls[0].inputs["pipeline_id"] == "001"


def test_execution_trace_record_multiple_tool_calls_ordered():
    trace = ExecutionTrace()
    trace.record_tool_call("tool_a")
    trace.record_tool_call("tool_b")
    trace.record_tool_call("tool_c")
    names = trace.tool_names_called()
    assert names == ["tool_a", "tool_b", "tool_c"]
    assert trace.tool_calls[2].order == 2


def test_execution_trace_record_file_change():
    trace = ExecutionTrace()
    trace.record_file_change("src/foo.py", via_managed_patch=True, patch_id="p1")
    assert len(trace.file_changes) == 1
    assert trace.file_changes[0].path == "src/foo.py"
    assert trace.file_changes[0].via_managed_patch is True


def test_execution_trace_add_evidence():
    trace = ExecutionTrace()
    trace.add_evidence("pytest: 100 passed")
    assert len(trace.evidence_refs) == 1
    assert trace.evidence_refs[0] == "pytest: 100 passed"


def test_execution_trace_tool_names_called():
    trace = ExecutionTrace()
    assert trace.tool_names_called() == []
    trace.record_tool_call("tool_x")
    trace.record_tool_call("tool_y")
    assert trace.tool_names_called() == ["tool_x", "tool_y"]


# ---------------------------------------------------------------------------
# ExecutionTrace — lifecycle advancement
# ---------------------------------------------------------------------------


def test_lifecycle_order_is_defined():
    assert LIFECYCLE_ORDER[0] == LifecycleStage.TASK_LOADED
    assert LIFECYCLE_ORDER[-1] == LifecycleStage.RESULT_FINALIZED
    assert len(LIFECYCLE_ORDER) == 6


def test_advance_lifecycle_forward():
    trace = ExecutionTrace()
    assert trace.lifecycle_stage == LifecycleStage.TASK_LOADED
    trace.advance_lifecycle(LifecycleStage.CONTEXT_ACQUIRED)
    assert trace.lifecycle_stage == LifecycleStage.CONTEXT_ACQUIRED


def test_advance_lifecycle_does_not_regress():
    trace = ExecutionTrace()
    trace.advance_lifecycle(LifecycleStage.CHANGES_APPLIED)
    trace.advance_lifecycle(LifecycleStage.CONTEXT_ACQUIRED)  # earlier stage
    assert trace.lifecycle_stage == LifecycleStage.CHANGES_APPLIED


# ---------------------------------------------------------------------------
# ExecutionTrace — fail-closed on finalized trace
# ---------------------------------------------------------------------------


def test_cannot_record_tool_call_after_finalized():
    trace = ExecutionTrace()
    trace.finalized = True
    with pytest.raises(RuntimeError, match="finalized"):
        trace.record_tool_call("tool_x")


def test_cannot_record_file_change_after_finalized():
    trace = ExecutionTrace()
    trace.finalized = True
    with pytest.raises(RuntimeError, match="finalized"):
        trace.record_file_change("foo.py", via_managed_patch=True)


def test_cannot_add_evidence_after_finalized():
    trace = ExecutionTrace()
    trace.finalized = True
    with pytest.raises(RuntimeError, match="finalized"):
        trace.add_evidence("some evidence")


# ---------------------------------------------------------------------------
# ExecutionTrace — persistence
# ---------------------------------------------------------------------------


def test_trace_save_and_load_roundtrip(tmp_path):
    trace = ExecutionTrace(pipeline_id="001", policy_mode="standard_code_change")
    trace.record_tool_call("govos_get_task_contract", inputs={"pipeline_id": "001"})
    trace.record_file_change("src/foo.py", via_managed_patch=True, patch_id="p1")
    trace.add_evidence("pytest: 10 passed")

    saved_path = trace.save(tmp_path)
    assert saved_path.exists()

    loaded = ExecutionTrace.load(tmp_path, trace.run_id)
    assert loaded.run_id == trace.run_id
    assert loaded.pipeline_id == "001"
    assert len(loaded.tool_calls) == 1
    assert len(loaded.file_changes) == 1
    assert loaded.evidence_refs == ["pytest: 10 passed"]


def test_trace_exists_returns_false_for_unknown(tmp_path):
    assert not ExecutionTrace.exists(tmp_path, "nonexistent-run-id")


def test_trace_exists_returns_true_after_save(tmp_path):
    trace = ExecutionTrace()
    trace.save(tmp_path)
    assert ExecutionTrace.exists(tmp_path, trace.run_id)


def test_trace_load_raises_for_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        ExecutionTrace.load(tmp_path, "no-such-run")
