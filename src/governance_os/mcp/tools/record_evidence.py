"""govos_record_evidence — record an evidence reference within a governed run.

Evidence references are structured claims that support the finalization summary.
They are required by the high_assurance_release policy before finalization.

Advances lifecycle to EVIDENCE_RECORDED.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_record_evidence(
    run_id: str,
    evidence_ref: str,
    root: str = ".",
) -> dict:
    """Record an evidence reference in the execution trace.

    Evidence references are free-form strings identifying artifacts, test results,
    review decisions, or other verifiable claims that support run completion.

    Examples of valid evidence refs:
    - "pytest: 519 passed in 2.12s"
    - "coverage: 94% (src/governance_os)"
    - "reviewer: approved by alice@example.com at 2026-03-26T12:00Z"
    - "artifact: artifacts/governance/reviews/2026-03-26-review.md"

    Args:
        run_id: Run identifier from govos_get_task_contract.
        evidence_ref: Evidence reference string (non-empty, max 500 chars).
        root: Repository root directory.

    Returns:
        dict with:
          run_id: str
          evidence_ref: str
          total_evidence: int — count of evidence refs recorded so far
          lifecycle_stage: str — EVIDENCE_RECORDED
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "evidence_ref": evidence_ref,
            "total_evidence": 0,
            "lifecycle_stage": "UNKNOWN",
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found.",
        }

    if not evidence_ref or not evidence_ref.strip():
        return {
            "run_id": run_id,
            "evidence_ref": evidence_ref,
            "total_evidence": 0,
            "lifecycle_stage": "UNKNOWN",
            "error": "CONTRACT_INPUT_INVALID: evidence_ref must be a non-empty string.",
        }

    if len(evidence_ref) > 500:
        return {
            "run_id": run_id,
            "evidence_ref": evidence_ref[:50] + "...",
            "total_evidence": 0,
            "lifecycle_stage": "UNKNOWN",
            "error": "CONTRACT_INPUT_INVALID: evidence_ref exceeds 500 character limit.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    if trace.finalized:
        return {
            "run_id": run_id,
            "evidence_ref": evidence_ref,
            "total_evidence": len(trace.evidence_refs),
            "lifecycle_stage": trace.lifecycle_stage,
            "error": "TOOL_POLICY_VIOLATION: run is finalized; no further evidence can be recorded.",
        }

    trace.add_evidence(evidence_ref.strip())
    trace.record_tool_call(
        "govos_record_evidence",
        inputs={"evidence_ref": evidence_ref.strip()},
        result_ok=True,
    )
    trace.advance_lifecycle(LifecycleStage.EVIDENCE_RECORDED)
    trace.save(root_path)

    return {
        "run_id": run_id,
        "evidence_ref": evidence_ref.strip(),
        "total_evidence": len(trace.evidence_refs),
        "lifecycle_stage": trace.lifecycle_stage,
        "error": None,
    }
