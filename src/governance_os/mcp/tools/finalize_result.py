"""govos_finalize_result — finalize a governed run and validate governance.

This is the mandatory exit tool for every governed run. It:
1. Loads the execution trace for the run.
2. Loads the governing ToolPolicy for the run's policy_mode.
3. Runs the governance validator against the trace.
4. Records the validation result in the trace.
5. Marks the trace as finalized (immutable from this point).
6. Persists the final trace to disk.

If validation fails, the result is returned with passed=False and a list
of violation codes. The run is still marked finalized (it is complete —
governance analysis is the result, not a gating condition for the record).

A run that is never finalized will fail Rule 4 of the validator when any
subsequent validation sweep occurs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage
from governance_os.contracts.tool_policy import POLICY_REGISTRY, STANDARD_CODE_CHANGE
from governance_os.runtime.validator import validate


def govos_finalize_result(
    run_id: str,
    summary: str,
    root: str = ".",
) -> dict:
    """Finalize a governed run and run governance validation.

    MUST be the last tool called in every governed run.
    Governance validation is performed at this point.

    Args:
        run_id: Run identifier returned by govos_get_task_contract.
        summary: Human-readable summary of what was accomplished in this run.
        root: Repository root directory.

    Returns:
        dict with:
          run_id: str
          validation_passed: bool
          failures: list[dict] — each with code and detail
          lifecycle_stage: str — RESULT_FINALIZED
          policy_mode: str
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "validation_passed": False,
            "failures": [
                {
                    "code": "CONTRACT_INPUT_INVALID",
                    "detail": f"Run '{run_id}' not found. Call govos_get_task_contract first.",
                }
            ],
            "lifecycle_stage": "UNKNOWN",
            "policy_mode": "unknown",
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    # Resolve policy
    policy = POLICY_REGISTRY.get(trace.policy_mode, STANDARD_CODE_CHANGE)

    # Record this finalize call in the trace before validating
    trace.record_tool_call(
        "govos_finalize_result",
        inputs={"summary": summary[:200]},  # truncate for trace storage
        result_ok=True,
    )
    trace.advance_lifecycle(LifecycleStage.RESULT_FINALIZED)

    # Mark finalized BEFORE validation so Rule 4 sees the finalized state
    trace.finalized = True
    trace.finalized_at = datetime.now(timezone.utc)
    trace.finalization_summary = summary

    # Validate against policy
    validation = validate(trace, policy)
    trace.validation_passed = validation.passed

    trace.save(root_path)

    return {
        "run_id": run_id,
        "validation_passed": validation.passed,
        "failures": [{"code": f.code, "detail": f.detail} for f in validation.failures],
        "lifecycle_stage": trace.lifecycle_stage,
        "policy_mode": policy.mode,
        "error": None,
    }
