"""govos_get_file_context — read a source file for context within a governed run.

Read-only. Records the read in the execution trace for auditability.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_get_file_context(
    run_id: str,
    file_path: str,
    root: str = ".",
    start_line: int = 1,
    end_line: int | None = None,
) -> dict:
    """Read a source file and return its content as context.

    Read-only operation. The file is not modified. Call is recorded in the trace.

    Args:
        run_id: Run identifier from govos_get_task_contract.
        file_path: Repository-relative path to the file to read.
        root: Repository root directory.
        start_line: First line to return (1-indexed, inclusive).
        end_line: Last line to return (1-indexed, inclusive). None = end of file.

    Returns:
        dict with:
          run_id: str
          file_path: str
          content: str — file content (sliced to requested line range)
          total_lines: int
          start_line: int
          end_line: int
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "file_path": file_path,
            "content": "",
            "total_lines": 0,
            "start_line": start_line,
            "end_line": 0,
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    # Safety — must stay within repo root
    target = (root_path / file_path).resolve()
    try:
        target.relative_to(root_path)
    except ValueError:
        return {
            "run_id": run_id,
            "file_path": file_path,
            "content": "",
            "total_lines": 0,
            "start_line": start_line,
            "end_line": 0,
            "error": f"CONTRACT_INPUT_INVALID: '{file_path}' escapes repository root.",
        }

    if not target.exists():
        return {
            "run_id": run_id,
            "file_path": file_path,
            "content": "",
            "total_lines": 0,
            "start_line": start_line,
            "end_line": 0,
            "error": f"CONTRACT_INPUT_INVALID: '{file_path}' does not exist.",
        }

    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)
    s = max(1, start_line)
    e = end_line if end_line is not None else total
    e = min(e, total)
    content = "\n".join(lines[s - 1 : e])

    trace.record_tool_call(
        "govos_get_file_context",
        inputs={"file_path": file_path, "start_line": s, "end_line": e},
        result_ok=True,
    )
    trace.advance_lifecycle(LifecycleStage.CONTEXT_ACQUIRED)
    trace.save(root_path)

    return {
        "run_id": run_id,
        "file_path": file_path,
        "content": content,
        "total_lines": total,
        "start_line": s,
        "end_line": e,
        "error": None,
    }
