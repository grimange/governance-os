"""Governance validator for MCP execution traces.

The validator applies a ToolPolicy to a completed (or in-progress) ExecutionTrace
and returns a machine-readable ValidationResult listing every governance violation.

Design principles:
- Deterministic: same trace + policy always produces the same result.
- Extensible: add new rules by appending to the internal rule list.
- Fail-closed: if required conditions are absent, the run is INVALID.
- Separation of concerns: validation is pure (no I/O, no side effects).

Rules enforced (in order):
  1. TOOL_POLICY_VIOLATION — required tools not present in trace.
  2. SEQUENCE_VIOLATION — required tool sequence not preserved.
  3. TOOL_BYPASS_DETECTED — file changes bypassed managed patch.
  4. EVIDENCE_MISSING — finalization required but trace not finalized.
  5. EVIDENCE_MISSING — evidence refs required but none recorded.
  6. TEST_EXECUTION_MISSING — test execution required but absent.
"""

from __future__ import annotations

from pydantic import BaseModel

from governance_os.contracts.execution_trace import ExecutionTrace
from governance_os.contracts.failure_codes import FailureCode
from governance_os.contracts.tool_policy import ToolPolicy


class FailureRecord(BaseModel):
    """A single governance violation detected by the validator."""

    code: FailureCode
    """Machine-readable violation code."""

    detail: str
    """Human-readable description of the violation."""

    model_config = {"frozen": True}


class ValidationResult(BaseModel):
    """Result of validating an ExecutionTrace against a ToolPolicy."""

    passed: bool
    """True only when zero failures are detected."""

    failures: list[FailureRecord] = []
    """Ordered list of all detected violations."""

    policy_mode: str = ""
    """Mode of the policy that was applied."""

    run_id: str = ""
    """Run ID of the trace that was validated."""

    model_config = {"frozen": True}

    def __str__(self) -> str:
        if self.passed:
            return f"PASS [{self.policy_mode}] run={self.run_id}"
        codes = ", ".join(f.code for f in self.failures)
        return f"FAIL [{self.policy_mode}] run={self.run_id} violations=[{codes}]"


def validate(trace: ExecutionTrace, policy: ToolPolicy) -> ValidationResult:
    """Validate an execution trace against a governance policy.

    Args:
        trace: The execution trace to validate.
        policy: The ToolPolicy to enforce.

    Returns:
        ValidationResult with passed=True and no failures if compliant.
        ValidationResult with passed=False and one or more FailureRecords otherwise.

    This function is pure: it never mutates trace or policy and performs no I/O.
    """
    failures: list[FailureRecord] = []
    called: list[str] = trace.tool_names_called()
    called_set: set[str] = set(called)

    # ------------------------------------------------------------------ #
    # Rule 1 — Required tools must appear in the trace
    # ------------------------------------------------------------------ #
    for tool in policy.required_tools:
        if tool not in called_set:
            failures.append(
                FailureRecord(
                    code=FailureCode.TOOL_POLICY_VIOLATION,
                    detail=f"Required tool '{tool}' was not called in run '{trace.run_id}'.",
                )
            )

    # ------------------------------------------------------------------ #
    # Rule 2 — Required sequence must be preserved
    # (only relative ordering is enforced — other tools may interleave)
    # ------------------------------------------------------------------ #
    if policy.required_sequence:
        # Find the first call position for each tool in the required sequence
        seq_positions: list[int | None] = []
        for tool in policy.required_sequence:
            positions = [i for i, t in enumerate(called) if t == tool]
            seq_positions.append(min(positions) if positions else None)

        for i in range(1, len(seq_positions)):
            prev_pos = seq_positions[i - 1]
            curr_pos = seq_positions[i]
            prev_name = policy.required_sequence[i - 1]
            curr_name = policy.required_sequence[i]
            if prev_pos is not None and curr_pos is not None and prev_pos >= curr_pos:
                failures.append(
                    FailureRecord(
                        code=FailureCode.SEQUENCE_VIOLATION,
                        detail=(
                            f"'{curr_name}' must be called after '{prev_name}' "
                            f"(positions: {prev_name}={prev_pos}, {curr_name}={curr_pos})."
                        ),
                    )
                )

    # ------------------------------------------------------------------ #
    # Rule 3 — File changes must use managed patch when policy requires it
    # ------------------------------------------------------------------ #
    if "unmanaged_write" in policy.forbidden_command_classes:
        for change in trace.file_changes:
            if not change.via_managed_patch:
                failures.append(
                    FailureRecord(
                        code=FailureCode.TOOL_BYPASS_DETECTED,
                        detail=(
                            f"File '{change.path}' was modified outside the managed patch tool "
                            f"(govos_write_patch). Policy '{policy.mode}' forbids unmanaged writes."
                        ),
                    )
                )

    # ------------------------------------------------------------------ #
    # Rule 4 — Completion requires finalization
    # ------------------------------------------------------------------ #
    if "govos_finalize_result" in policy.required_before_complete and not trace.finalized:
        failures.append(
            FailureRecord(
                code=FailureCode.EVIDENCE_MISSING,
                detail=(
                    "Run not finalized. 'govos_finalize_result' must be called "
                    "before the run can be considered complete."
                ),
            )
        )

    # ------------------------------------------------------------------ #
    # Rule 5 — Evidence required when policy demands it
    # ------------------------------------------------------------------ #
    if "govos_record_evidence" in policy.required_tools and not trace.evidence_refs:
        failures.append(
            FailureRecord(
                code=FailureCode.EVIDENCE_MISSING,
                detail=(
                    "No evidence recorded. 'govos_record_evidence' must be called "
                    "with at least one evidence reference before finalization."
                ),
            )
        )

    # ------------------------------------------------------------------ #
    # Rule 6 — Test execution required when policy demands it
    # ------------------------------------------------------------------ #
    if "govos_run_tests" in policy.required_tools and "govos_run_tests" not in called_set:
        failures.append(
            FailureRecord(
                code=FailureCode.TEST_EXECUTION_MISSING,
                detail=(
                    "Test execution required by policy but 'govos_run_tests' was not called. "
                    "Run tests before finalizing."
                ),
            )
        )

    return ValidationResult(
        passed=len(failures) == 0,
        failures=failures,
        policy_mode=policy.mode,
        run_id=trace.run_id,
    )
