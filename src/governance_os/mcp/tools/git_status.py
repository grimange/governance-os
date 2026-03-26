"""govos_git_status — return git status within a governed run.

Read-only. Not a general git command runner — only `git status --short` is invoked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_git_status(run_id: str, root: str = ".") -> dict:
    """Return git status of the repository.

    Read-only. Records the call in the execution trace for auditability.
    Only invokes 'git status --short' — not a generic git command tool.

    Args:
        run_id: Run identifier from govos_get_task_contract.
        root: Repository root directory.

    Returns:
        dict with:
          run_id: str
          branch: str — current branch name
          modified: list[str] — modified file paths
          untracked: list[str] — untracked file paths
          staged: list[str] — staged file paths
          clean: bool — True if working tree is clean
          lifecycle_stage: str
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "branch": "",
            "modified": [],
            "untracked": [],
            "staged": [],
            "clean": False,
            "lifecycle_stage": "UNKNOWN",
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    # Get current branch
    branch_proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, cwd=root_path, timeout=10,
    )
    branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "unknown"

    # Get status
    status_proc = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True, text=True, cwd=root_path, timeout=10,
    )

    modified, untracked, staged = [], [], []
    if status_proc.returncode == 0:
        for line in status_proc.stdout.splitlines():
            if len(line) < 3:
                continue
            xy = line[:2]
            path = line[3:].strip()
            if xy[0] in "MADRCU":
                staged.append(path)
            if xy[1] == "M":
                modified.append(path)
            elif xy[1] == "?":
                untracked.append(path)

    clean = not (modified or untracked or staged)

    trace.record_tool_call(
        "govos_git_status",
        inputs={"branch": branch},
        result_ok=True,
    )
    trace.advance_lifecycle(LifecycleStage.CONTEXT_ACQUIRED)
    trace.save(root_path)

    return {
        "run_id": run_id,
        "branch": branch,
        "modified": modified,
        "untracked": untracked,
        "staged": staged,
        "clean": clean,
        "lifecycle_stage": trace.lifecycle_stage,
        "error": None,
    }
