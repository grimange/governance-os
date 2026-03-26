"""govos_run_tests — run the project test suite within a governed run.

Specific to pytest. Not a generic shell execution tool.
Advances lifecycle to VERIFICATION_COMPLETED on completion.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from governance_os.contracts.execution_trace import ExecutionTrace, LifecycleStage


def govos_run_tests(
    run_id: str,
    root: str = ".",
    test_path: str = "tests",
    extra_args: list[str] | None = None,
) -> dict:
    """Run the pytest test suite and record results in the execution trace.

    This tool is bounded to pytest execution only. It is not a generic
    shell execution tool. Only --tb, -q, --no-header flags are internally used;
    extra_args are restricted to test selection patterns (paths, -k, -m flags).

    Args:
        run_id: Run identifier from govos_get_task_contract.
        root: Repository root directory.
        test_path: Relative path to the tests directory (default: "tests").
        extra_args: Optional list of restricted pytest arguments
            (e.g. ["tests/test_lifecycle.py", "-k", "test_parse"]).
            Raw shell commands are not accepted.

    Returns:
        dict with:
          run_id: str
          passed: bool
          exit_code: int
          summary: str — last line of pytest output
          output: str — full pytest stdout+stderr
          lifecycle_stage: str — VERIFICATION_COMPLETED
          error: str | None
    """
    root_path = Path(root).resolve()

    if not ExecutionTrace.exists(root_path, run_id):
        return {
            "run_id": run_id,
            "passed": False,
            "exit_code": -1,
            "summary": "",
            "output": "",
            "lifecycle_stage": "UNKNOWN",
            "error": f"CONTRACT_INPUT_INVALID: run '{run_id}' not found.",
        }

    trace = ExecutionTrace.load(root_path, run_id)

    # Restrict extra_args to safe pytest selectors only
    allowed_flags = {"-k", "-m", "-v", "-q", "--tb", "-x", "--no-header", "-p"}
    safe_extra: list[str] = []
    if extra_args:
        for arg in extra_args:
            if arg.startswith("-"):
                flag = arg.split("=")[0]
                if flag not in allowed_flags:
                    return {
                        "run_id": run_id,
                        "passed": False,
                        "exit_code": -1,
                        "summary": "",
                        "output": "",
                        "lifecycle_stage": trace.lifecycle_stage,
                        "error": (
                            f"CONTRACT_INPUT_INVALID: flag '{flag}' is not in the "
                            "allowed pytest argument set."
                        ),
                    }
            safe_extra.append(arg)

    cmd = [
        "python", "-m", "pytest",
        str(root_path / test_path),
        "--tb=short", "-q", "--no-header",
    ] + safe_extra

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=root_path,
        timeout=300,
    )

    output = (proc.stdout + proc.stderr).strip()
    passed = proc.returncode == 0
    summary = output.splitlines()[-1] if output else ""

    trace.record_tool_call(
        "govos_run_tests",
        inputs={"test_path": test_path, "passed": passed, "exit_code": proc.returncode},
        result_ok=passed,
    )
    trace.advance_lifecycle(LifecycleStage.VERIFICATION_COMPLETED)
    trace.save(root_path)

    return {
        "run_id": run_id,
        "passed": passed,
        "exit_code": proc.returncode,
        "summary": summary,
        "output": output,
        "lifecycle_stage": trace.lifecycle_stage,
        "error": None,
    }
