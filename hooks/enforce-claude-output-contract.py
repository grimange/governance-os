#!/usr/bin/env python3
"""
enforce-claude-output-contract.py

Hook script to enforce Governance OS Claude output contract.
Intended for use in git hooks, CI pipelines, or pre-commit checks.

This wraps validate-claude-output.py and enforces strict rejection rules.

Exit codes:
    0 = pass
    1 = reject
"""

import subprocess
import sys
from pathlib import Path


def run_validator(output_path: str, failure_codes_path: str | None = None) -> int:
    cmd = [
        "python",
        "validate-claude-output.py",
        "--input",
        output_path,
    ]

    if failure_codes_path:
        cmd.extend(["--failure-codes", failure_codes_path])

    result = subprocess.run(cmd)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: enforce-claude-output-contract.py <output_file> [failure_codes_file]")
        return 1

    output_file = sys.argv[1]
    failure_codes_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(output_file).exists():
        print(f"Reject: output file not found: {output_file}")
        return 1

    rc = run_validator(output_file, failure_codes_file)

    if rc != 0:
        print("Reject: Claude output failed validation")
        return 1

    print("Pass: Claude output is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
