"""govos_search_code — search source code within a governed run.

Read-only operation. Advances lifecycle to CONTEXT_ACQUIRED if not already there.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_search_code(
    run_id: str,
    pattern: str,
    file_glob: str = "**/*.py",
    root: str = ".",
    max_results: int = 50,
) -> dict:
    """Search source code for a pattern within the governed repo.

    Read-only. Records the search in the execution trace for auditability.

    Args:
        run_id: Run identifier from govos_get_task_contract.
        pattern: Regular expression pattern to search for.
        file_glob: Glob pattern limiting which files are searched (default: **/*.py).
        root: Repository root directory.
        max_results: Maximum number of matching lines to return.

    Returns:
        dict with:
          run_id: str
          pattern: str
          matches: list[dict] — each with file (str), line (int), text (str)
          total_matches: int
          truncated: bool — True if results were cut at max_results
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "pattern": pattern,
            "matches": [],
            "total_matches": 0,
            "truncated": False,
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    matches = []
    try:
        compiled = re.compile(pattern)
        for file_path in sorted(root_path.glob(file_glob)):
            if not file_path.is_file():
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if compiled.search(line):
                    matches.append(
                        {
                            "file": str(file_path.relative_to(root_path)),
                            "line": lineno,
                            "text": line.rstrip(),
                        }
                    )
    except re.error as exc:
        return {
            "run_id": run_id,
            "pattern": pattern,
            "matches": [],
            "total_matches": 0,
            "truncated": False,
            "error": f"CONTRACT_INPUT_INVALID: invalid regex pattern: {exc}",
        }

    total = len(matches)
    truncated = total > max_results
    matches = matches[:max_results]

    trace.record_tool_call(
        "govos_search_code",
        inputs={"pattern": pattern, "file_glob": file_glob},
        result_ok=True,
    )
    trace.advance_lifecycle(LifecycleStage.CONTEXT_ACQUIRED)
    trace.save(root_path)

    return {
        "run_id": run_id,
        "pattern": pattern,
        "matches": matches,
        "total_matches": total,
        "truncated": truncated,
        "error": None,
    }
