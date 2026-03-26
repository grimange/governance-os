"""govos_run_lint — run the project linter within a governed run.

Specific to ruff. Not a generic shell execution tool.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_run_lint(
    run_id: str,
    root: str = ".",
    target: str = "src",
) -> dict:
    """Run ruff lint and return results recorded in the execution trace.

    Bounded to ruff check. Not a generic shell execution tool.

    Args:
        run_id: Run identifier from govos_get_task_contract.
        root: Repository root directory.
        target: Directory or file path to lint (default: "src").

    Returns:
        dict with:
          run_id: str
          passed: bool — True if no lint violations found
          exit_code: int
          violations: list[str] — ruff output lines
          violation_count: int
          lifecycle_stage: str
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "passed": False,
            "exit_code": -1,
            "violations": [],
            "violation_count": 0,
            "lifecycle_stage": "UNKNOWN",
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    cmd = ["python", "-m", "ruff", "check", str(root_path / target), "--output-format=text"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=root_path,
        timeout=120,
    )

    output_lines = (proc.stdout + proc.stderr).strip().splitlines()
    passed = proc.returncode == 0
    violations = [ln for ln in output_lines if ln.strip()]

    trace.record_tool_call(
        "govos_run_lint",
        inputs={"target": target, "passed": passed, "exit_code": proc.returncode},
        result_ok=passed,
    )
    trace.save(root_path)

    return {
        "run_id": run_id,
        "passed": passed,
        "exit_code": proc.returncode,
        "violations": violations,
        "violation_count": len(violations),
        "lifecycle_stage": trace.lifecycle_stage,
        "error": None,
    }
