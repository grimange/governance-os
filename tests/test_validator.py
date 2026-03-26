"""Tests for Phase 2 — governance validator.

Each test targets a specific validation rule and verifies both pass and fail cases.
"""

from __future__ import annotations

from governance_os.contracts.execution_trace import ExecutionTrace
from governance_os.contracts.failure_codes import FailureCode
from governance_os.contracts.tool_policy import (
    HIGH_ASSURANCE_RELEASE,
    READ_ONLY_AUDIT,
    STANDARD_CODE_CHANGE,
    ToolPolicy,
)
from governance_os.runtime.validator import FailureRecord, ValidationResult, validate


# ---------------------------------------------------------------------------
# ValidationResult model
# ---------------------------------------------------------------------------


def test_validation_result_passed():
    result = ValidationResult(passed=True, policy_mode="test", run_id="abc")
    assert result.passed is True
    assert result.failures == []


def test_validation_result_failed():
    result = ValidationResult(
        passed=False,
        failures=[FailureRecord(code=FailureCode.TOOL_POLICY_VIOLATION, detail="missing tool")],
        policy_mode="test",
        run_id="abc",
    )
    assert result.passed is False
    assert len(result.failures) == 1


def test_validation_result_str_pass():
    result = ValidationResult(passed=True, policy_mode="standard", run_id="r1")
    assert "PASS" in str(result)
    assert "standard" in str(result)


def test_validation_result_str_fail():
    result = ValidationResult(
        passed=False,
        failures=[FailureRecord(code=FailureCode.SEQUENCE_VIOLATION, detail="x")],
        policy_mode="test",
        run_id="r1",
    )
    assert "FAIL" in str(result)
    assert "SEQUENCE_VIOLATION" in str(result)


def test_failure_record_is_frozen():
    import pytest

    rec = FailureRecord(code=FailureCode.TOOL_POLICY_VIOLATION, detail="test")
    with pytest.raises(Exception):
        rec.detail = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Rule 1 — Required tools must appear in trace
# ---------------------------------------------------------------------------


def _minimal_finalized_trace(tools: list[str]) -> ExecutionTrace:
    trace = ExecutionTrace(policy_mode="standard_code_change")
    for tool in tools:
        trace.record_tool_call(tool)
    trace.finalized = True
    return trace


def test_rule1_pass_all_required_tools_present():
    trace = _minimal_finalized_trace(
        ["govos_get_task_contract", "govos_read_repo_map", "govos_write_patch", "govos_finalize_result"]
    )
    result = validate(trace, STANDARD_CODE_CHANGE)
    rule1_failures = [f for f in result.failures if f.code == FailureCode.TOOL_POLICY_VIOLATION]
    # May still fail other rules, but rule1 should pass
    assert all("govos_" not in f.detail or "Required tool" not in f.detail for f in rule1_failures)


def test_rule1_fail_missing_required_tool():
    trace = _minimal_finalized_trace(["govos_get_task_contract", "govos_finalize_result"])
    result = validate(trace, STANDARD_CODE_CHANGE)
    codes = [f.code for f in result.failures]
    assert FailureCode.TOOL_POLICY_VIOLATION in codes
    details = " ".join(f.detail for f in result.failures)
    assert "govos_write_patch" in details


def test_rule1_fail_completely_empty_trace():
    trace = ExecutionTrace(policy_mode="standard_code_change")
    result = validate(trace, STANDARD_CODE_CHANGE)
    assert not result.passed
    assert len(result.failures) > 0


def test_rule1_read_only_audit_missing_repo_map():
    trace = _minimal_finalized_trace(["govos_get_task_contract", "govos_finalize_result"])
    result = validate(trace, READ_ONLY_AUDIT)
    # govos_read_repo_map is required by READ_ONLY_AUDIT
    codes = [f.code for f in result.failures]
    assert FailureCode.TOOL_POLICY_VIOLATION in codes


def test_rule1_pass_when_required_tools_covered():
    trace = _minimal_finalized_trace(
        ["govos_get_task_contract", "govos_read_repo_map", "govos_finalize_result"]
    )
    result = validate(trace, READ_ONLY_AUDIT)
    tool_violations = [f for f in result.failures if f.code == FailureCode.TOOL_POLICY_VIOLATION]
    assert tool_violations == []


# ---------------------------------------------------------------------------
# Rule 2 — Required sequence must be preserved
# ---------------------------------------------------------------------------


def test_rule2_pass_correct_sequence():
    trace = _minimal_finalized_trace(
        ["govos_get_task_contract", "govos_write_patch", "govos_finalize_result"]
    )
    result = validate(trace, STANDARD_CODE_CHANGE)
    seq_failures = [f for f in result.failures if f.code == FailureCode.SEQUENCE_VIOLATION]
    assert seq_failures == []


def test_rule2_fail_finalize_before_write():
    trace = _minimal_finalized_trace(
        ["govos_get_task_contract", "govos_finalize_result", "govos_write_patch"]
    )
    result = validate(trace, STANDARD_CODE_CHANGE)
    seq_failures = [f for f in result.failures if f.code == FailureCode.SEQUENCE_VIOLATION]
    assert len(seq_failures) > 0


def test_rule2_fail_write_before_contract():
    trace = _minimal_finalized_trace(
        ["govos_write_patch", "govos_get_task_contract", "govos_finalize_result"]
    )
    result = validate(trace, STANDARD_CODE_CHANGE)
    seq_failures = [f for f in result.failures if f.code == FailureCode.SEQUENCE_VIOLATION]
    assert len(seq_failures) > 0


def test_rule2_interleaved_tools_ok():
    """Non-sequence tools may appear anywhere."""
    trace = _minimal_finalized_trace(
        [
            "govos_get_task_contract",
            "govos_read_repo_map",   # not in required_sequence
            "govos_write_patch",
            "govos_search_code",     # not in required_sequence
            "govos_finalize_result",
        ]
    )
    result = validate(trace, STANDARD_CODE_CHANGE)
    seq_failures = [f for f in result.failures if f.code == FailureCode.SEQUENCE_VIOLATION]
    assert seq_failures == []


def test_rule2_empty_required_sequence_skips_check():
    policy = ToolPolicy(mode="minimal", required_tools=["tool_a"])
    trace = _minimal_finalized_trace(["tool_a"])
    trace.finalized = True
    result = validate(trace, policy)
    seq_failures = [f for f in result.failures if f.code == FailureCode.SEQUENCE_VIOLATION]
    assert seq_failures == []


# ---------------------------------------------------------------------------
# Rule 3 — Unmanaged file writes are violations
# ---------------------------------------------------------------------------


def test_rule3_pass_managed_file_change():
    trace = ExecutionTrace(policy_mode="standard_code_change")
    trace.record_tool_call("govos_get_task_contract")
    trace.record_tool_call("govos_read_repo_map")
    trace.record_tool_call("govos_write_patch")
    trace.record_file_change("src/foo.py", via_managed_patch=True)
    trace.record_tool_call("govos_finalize_result")
    trace.finalized = True

    result = validate(trace, STANDARD_CODE_CHANGE)
    bypass_failures = [f for f in result.failures if f.code == FailureCode.TOOL_BYPASS_DETECTED]
    assert bypass_failures == []


def test_rule3_fail_unmanaged_file_change_with_policy_restriction():
    trace = ExecutionTrace(policy_mode="standard_code_change")
    trace.record_tool_call("govos_get_task_contract")
    trace.record_tool_call("govos_write_patch")
    trace.record_file_change("src/foo.py", via_managed_patch=False)  # bypass!
    trace.record_tool_call("govos_finalize_result")
    trace.finalized = True

    result = validate(trace, STANDARD_CODE_CHANGE)
    bypass_failures = [f for f in result.failures if f.code == FailureCode.TOOL_BYPASS_DETECTED]
    assert len(bypass_failures) == 1
    assert "src/foo.py" in bypass_failures[0].detail


def test_rule3_no_bypass_check_when_not_forbidden():
    policy = ToolPolicy(mode="permissive", required_tools=["tool_a"])
    trace = ExecutionTrace(policy_mode="permissive")
    trace.record_tool_call("tool_a")
    trace.record_file_change("foo.py", via_managed_patch=False)
    trace.finalized = True

    result = validate(trace, policy)
    bypass_failures = [f for f in result.failures if f.code == FailureCode.TOOL_BYPASS_DETECTED]
    assert bypass_failures == []


# ---------------------------------------------------------------------------
# Rule 4 — Finalization required
# ---------------------------------------------------------------------------


def test_rule4_fail_not_finalized():
    trace = ExecutionTrace(policy_mode="standard_code_change")
    trace.record_tool_call("govos_get_task_contract")
    trace.record_tool_call("govos_write_patch")
    # Note: trace.finalized is False (default)

    result = validate(trace, STANDARD_CODE_CHANGE)
    evidence_failures = [f for f in result.failures if f.code == FailureCode.EVIDENCE_MISSING]
    assert len(evidence_failures) >= 1


def test_rule4_pass_when_finalized():
    trace = _minimal_finalized_trace(
        ["govos_get_task_contract", "govos_read_repo_map", "govos_write_patch", "govos_finalize_result"]
    )
    result = validate(trace, STANDARD_CODE_CHANGE)
    evidence_failures = [f for f in result.failures if f.code == FailureCode.EVIDENCE_MISSING]
    assert evidence_failures == []


# ---------------------------------------------------------------------------
# Rule 5 — Evidence required for high assurance
# ---------------------------------------------------------------------------


def test_rule5_fail_no_evidence_high_assurance():
    trace = ExecutionTrace(policy_mode="high_assurance_release")
    for tool in ["govos_get_task_contract", "govos_read_repo_map", "govos_write_patch",
                 "govos_run_tests", "govos_record_evidence", "govos_finalize_result"]:
        trace.record_tool_call(tool)
    trace.finalized = True
    # No evidence refs added

    result = validate(trace, HIGH_ASSURANCE_RELEASE)
    evidence_failures = [f for f in result.failures if f.code == FailureCode.EVIDENCE_MISSING]
    assert len(evidence_failures) >= 1


def test_rule5_pass_with_evidence():
    trace = ExecutionTrace(policy_mode="high_assurance_release")
    for tool in ["govos_get_task_contract", "govos_read_repo_map", "govos_write_patch",
                 "govos_run_tests", "govos_record_evidence", "govos_finalize_result"]:
        trace.record_tool_call(tool)
    trace.add_evidence("pytest: 519 passed")
    trace.finalized = True

    result = validate(trace, HIGH_ASSURANCE_RELEASE)
    evidence_failures = [f for f in result.failures if f.code == FailureCode.EVIDENCE_MISSING]
    # Only finalization-specific rule may fire; evidence ref rule should pass
    ref_failures = [f for f in evidence_failures
                    if "govos_record_evidence" in f.detail and "No evidence" in f.detail]
    assert ref_failures == []


# ---------------------------------------------------------------------------
# Rule 6 — Test execution required for high assurance
# ---------------------------------------------------------------------------


def test_rule6_fail_no_test_run():
    trace = ExecutionTrace(policy_mode="high_assurance_release")
    for tool in ["govos_get_task_contract", "govos_write_patch", "govos_record_evidence",
                 "govos_finalize_result"]:
        trace.record_tool_call(tool)
    trace.add_evidence("manual review")
    trace.finalized = True

    result = validate(trace, HIGH_ASSURANCE_RELEASE)
    test_failures = [f for f in result.failures if f.code == FailureCode.TEST_EXECUTION_MISSING]
    assert len(test_failures) >= 1


def test_rule6_pass_when_tests_run():
    trace = ExecutionTrace(policy_mode="high_assurance_release")
    for tool in ["govos_get_task_contract", "govos_read_repo_map", "govos_write_patch",
                 "govos_run_tests", "govos_record_evidence", "govos_finalize_result"]:
        trace.record_tool_call(tool)
    trace.add_evidence("pytest: all passed")
    trace.finalized = True

    result = validate(trace, HIGH_ASSURANCE_RELEASE)
    test_failures = [f for f in result.failures if f.code == FailureCode.TEST_EXECUTION_MISSING]
    assert test_failures == []


# ---------------------------------------------------------------------------
# Full-run integration scenarios
# ---------------------------------------------------------------------------


def test_clean_standard_run_passes():
    """Complete standard_code_change run with correct tool ordering."""
    trace = ExecutionTrace(policy_mode="standard_code_change")
    trace.record_tool_call("govos_get_task_contract", inputs={"pipeline_id": "001"})
    trace.record_tool_call("govos_read_repo_map")
    trace.record_tool_call("govos_write_patch")
    trace.record_file_change("src/myfile.py", via_managed_patch=True, patch_id="p1")
    trace.record_tool_call("govos_finalize_result")
    trace.finalized = True

    result = validate(trace, STANDARD_CODE_CHANGE)
    assert result.passed, f"Expected pass but got failures: {[f.detail for f in result.failures]}"


def test_read_only_audit_with_no_writes_passes():
    trace = ExecutionTrace(policy_mode="read_only_audit")
    trace.record_tool_call("govos_get_task_contract")
    trace.record_tool_call("govos_read_repo_map")
    trace.record_tool_call("govos_finalize_result")
    trace.finalized = True

    result = validate(trace, READ_ONLY_AUDIT)
    assert result.passed, f"Expected pass but got failures: {[f.detail for f in result.failures]}"


def test_validator_result_carries_policy_and_run_info():
    trace = ExecutionTrace(policy_mode="standard_code_change")
    result = validate(trace, STANDARD_CODE_CHANGE)
    assert result.policy_mode == "standard_code_change"
    assert result.run_id == trace.run_id
