"""govos_read_repo_map — read the governance repo map for context acquisition.

Returns a structured map of all pipeline contracts and their lifecycle states.
Advances the run lifecycle to CONTEXT_ACQUIRED.

This tool should be called after govos_get_task_contract to establish full
repo context before making any changes.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_read_repo_map(run_id: str, root: str = ".") -> dict:
    """Return the governance repo map: all pipelines with lifecycle states.

    Advances the run lifecycle stage to CONTEXT_ACQUIRED.
    Call this after govos_get_task_contract to establish execution context.

    Args:
        run_id: Run identifier returned by govos_get_task_contract.
        root: Repository root directory (default: current working directory).

    Returns:
        dict with:
          run_id: str
          lifecycle_stage: str — CONTEXT_ACQUIRED
          pipelines: list[dict] — each pipeline with id, slug, title,
            declared_state, effective_state, drift
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "lifecycle_stage": "UNKNOWN",
            "pipelines": [],
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found. "
            "Call govos_get_task_contract first.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    import governance_os.api as api

    lifecycle_result = api.pipeline_lifecycle(root_path)

    pipelines_out = []
    for record in lifecycle_result.records:
        pipelines_out.append(
            {
                "id": record.pipeline_id,
                "slug": record.slug,
                "declared_state": record.declared_state,
                "effective_state": record.effective_state.value,
                "drift": record.drift,
                "reasons": record.reasons,
            }
        )

    trace.record_tool_call(
        "govos_read_repo_map",
        inputs={"root": root},
        result_ok=True,
    )
    trace.advance_lifecycle(LifecycleStage.CONTEXT_ACQUIRED)
    trace.save(root_path)

    return {
        "run_id": run_id,
        "lifecycle_stage": trace.lifecycle_stage,
        "pipelines": pipelines_out,
        "error": None,
    }
