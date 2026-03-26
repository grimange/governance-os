"""govos_get_task_contract — load a pipeline contract for a governed run.

This is the mandatory entry-point tool for all governed runs. It:
1. Loads and returns the pipeline contract for the specified pipeline ID.
2. Initialises an ExecutionTrace for the run with a fresh run_id.
3. Persists the trace to artifacts/governance/mcp-runs/<run_id>/trace.json.

The returned run_id must be passed to all subsequent governed tools.

Governance note: if the pipeline contract cannot be loaded, the run must
not proceed — return the failure code CONTRACT_INPUT_INVALID to the caller.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_get_task_contract(
    pipeline_id: str,
    root: str = ".",
    policy_mode: str = "standard_code_change",
) -> dict:
    """Load a pipeline contract and initialise a governed run trace.

    This tool MUST be called first in every governed run.
    The run_id returned here must be passed to all subsequent governed tools.

    Args:
        pipeline_id: Numeric ID (e.g. "001") or slug of the pipeline contract.
        root: Repository root directory (default: current working directory).
        policy_mode: Governance policy to enforce.
            One of: "read_only_audit", "standard_code_change", "high_assurance_release".

    Returns:
        dict with:
          run_id: str — unique run identifier (pass to all subsequent tools)
          pipeline_id: str — resolved pipeline ID
          contract: dict — pipeline contract fields
          lifecycle_stage: str — current run stage (TASK_LOADED)
          error: str | None — CONTRACT_INPUT_INVALID if contract not found
    """
    root_path = Path(root).resolve()

    # Import here to avoid circular imports at module load time
    import governance_os.api as api

    result = api.scan(root_path)

    # Find pipeline by ID or slug
    pipeline = None
    for p in result.pipelines:
        if p.numeric_id == pipeline_id or p.slug == pipeline_id:
            pipeline = p
            break

    trace = ExecutionTrace(
        pipeline_id=pipeline_id if pipeline else None,
        policy_mode=policy_mode,
    )

    if pipeline is None:
        trace.record_tool_call(
            "govos_get_task_contract",
            inputs={"pipeline_id": pipeline_id, "policy_mode": policy_mode},
            result_ok=False,
        )
        trace.save(root_path)
        return {
            "run_id": trace.run_id,
            "pipeline_id": pipeline_id,
            "contract": None,
            "lifecycle_stage": trace.lifecycle_stage,
            "error": f"CONTRACT_INPUT_INVALID: pipeline '{pipeline_id}' not found in {root_path}",
        }

    trace.record_tool_call(
        "govos_get_task_contract",
        inputs={"pipeline_id": pipeline_id, "policy_mode": policy_mode},
        result_ok=True,
    )
    trace.advance_lifecycle(LifecycleStage.TASK_LOADED)
    trace.save(root_path)

    return {
        "run_id": trace.run_id,
        "pipeline_id": pipeline.numeric_id,
        "contract": {
            "id": pipeline.numeric_id,
            "slug": pipeline.slug,
            "title": pipeline.title,
            "stage": pipeline.stage,
            "scope": pipeline.scope,
            "purpose": pipeline.purpose,
            "depends_on": pipeline.depends_on,
            "inputs": pipeline.inputs,
            "outputs": pipeline.outputs,
            "success_criteria": pipeline.success_criteria,
            "declared_state": pipeline.declared_state,
        },
        "lifecycle_stage": trace.lifecycle_stage,
        "error": None,
    }
