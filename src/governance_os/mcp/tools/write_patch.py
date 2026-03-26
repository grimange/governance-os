"""govos_write_patch — apply a managed file change within a governed run.

All file changes MUST go through this tool when the active policy forbids
unmanaged writes. Writes applied outside this tool are classified as
TOOL_BYPASS_DETECTED violations at finalization.

Safety guardrails:
- Path must be within the repository root (no path traversal).
- Finalized traces are rejected (no changes after finalization).
- Every write is recorded in the execution trace as a managed patch.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_write_patch(
    run_id: str,
    file_path: str,
    new_content: str,
    root: str = ".",
) -> dict:
    """Apply a managed file change within a governed run.

    This is the ONLY governed path for file mutation. All file changes that
    should be visible to the governance validator must use this tool.
    Changes made via other mechanisms will be treated as TOOL_BYPASS_DETECTED.

    Args:
        run_id: Run identifier returned by govos_get_task_contract.
        file_path: Repository-relative path to write (must not escape repo root).
        new_content: Complete new file content (UTF-8).
        root: Repository root directory.

    Returns:
        dict with:
          run_id: str
          patch_id: str — unique identifier for this patch
          file_path: str — the relative path written
          bytes_written: int
          lifecycle_stage: str — CHANGES_APPLIED
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "patch_id": None,
            "file_path": file_path,
            "bytes_written": 0,
            "lifecycle_stage": "UNKNOWN",
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    if trace.finalized:
        return {
            "run_id": run_id,
            "patch_id": None,
            "file_path": file_path,
            "bytes_written": 0,
            "lifecycle_stage": trace.lifecycle_stage,
            "error": "TOOL_POLICY_VIOLATION: run is already finalized; no further changes allowed.",
        }

    # Path safety — must resolve inside repo root
    target = (root_path / file_path).resolve()
    try:
        target.relative_to(root_path)
    except ValueError:
        return {
            "run_id": run_id,
            "patch_id": None,
            "file_path": file_path,
            "bytes_written": 0,
            "lifecycle_stage": trace.lifecycle_stage,
            "error": (
                f"CONTRACT_INPUT_INVALID: '{file_path}' escapes repository root. "
                "Only repo-relative paths are permitted."
            ),
        }

    patch_id = str(uuid.uuid4())
    content_bytes = new_content.encode("utf-8")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content_bytes)

    trace.record_tool_call(
        "govos_write_patch",
        inputs={
            "file_path": file_path,
            "patch_id": patch_id,
            "bytes": len(content_bytes),
            "sha256": hashlib.sha256(content_bytes).hexdigest(),
        },
        result_ok=True,
    )
    trace.record_file_change(file_path, via_managed_patch=True, patch_id=patch_id)
    trace.advance_lifecycle(LifecycleStage.CHANGES_APPLIED)
    trace.save(root_path)

    return {
        "run_id": run_id,
        "patch_id": patch_id,
        "file_path": file_path,
        "bytes_written": len(content_bytes),
        "lifecycle_stage": trace.lifecycle_stage,
        "error": None,
    }
