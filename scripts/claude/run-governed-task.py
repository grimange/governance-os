#!/usr/bin/env python3
"""
run-governed-task.py

Governance OS wrapper for executing a structured Claude task with contract,
skills, and output validation.

This script is model-provider agnostic at the prompt-construction layer.
By default, it builds a governed execution prompt and writes it to disk.
If a command is supplied via --exec, it will invoke that command and pass
the prompt over stdin.

Typical usage:

    python scripts/claude/run-governed-task.py \
      --contract CLAUDE.md \
      --task templates/claude/verification-task.yaml \
      --skill skills/verify-frontmatter-schema/SKILL.md \
      --output artifacts/claude/example-output.txt \
      --prompt-out artifacts/claude/example-prompt.txt

Example with external executor:

    python scripts/claude/run-governed-task.py \
      --contract CLAUDE.md \
      --task task.yaml \
      --skill skills/produce-fail-closed-verdict/SKILL.md \
      --output out.txt \
      --prompt-out prompt.txt \
      --exec "claude -p"

Exit codes:
    0 = success
    1 = execution or validation failure
    2 = invalid invocation or task contract violation
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_TASK_FIELDS = {
    "task_id",
    "task_type",
    "objective",
    "inputs",
    "context",
    "constraints",
    "expected_output",
    "fail_closed_conditions",
}

DEFAULT_ALLOWED_FAILURE_CODES = {
    "INPUT_INSUFFICIENT",
    "AMBIGUOUS_TASK",
    "CONSTRAINT_VIOLATION",
    "MISSING_REFERENCE",
    "FORMAT_UNSATISFIABLE",
    "AUTHORIZATION_MISSING",
    "PATH_NON_PORTABLE",
    "UNSUPPORTED_ASSERTION_RISK",
}


def read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_yaml_or_json(path: Path) -> dict[str, Any]:
    """
    Load YAML if PyYAML is available; otherwise load JSON.
    """
    raw = read_text(path)
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Task file must contain a top-level object")
        return data

    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "PyYAML is required for .yaml/.yml task files. "
            "Install pyyaml or use JSON."
        ) from exc

    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("Task file must contain a top-level mapping")
    return data


def validate_task_schema(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = sorted(REQUIRED_TASK_FIELDS - set(task.keys()))
    if missing:
        errors.append(f"Missing required task fields: {', '.join(missing)}")

    if "objective" in task and not str(task["objective"]).strip():
        errors.append("Field 'objective' must be non-empty")

    if "constraints" in task and not isinstance(task["constraints"], list):
        errors.append("Field 'constraints' must be a list")

    if "fail_closed_conditions" in task and not isinstance(task["fail_closed_conditions"], list):
        errors.append("Field 'fail_closed_conditions' must be a list")

    if "expected_output" in task and not isinstance(task["expected_output"], dict):
        errors.append("Field 'expected_output' must be a mapping")

    return errors


def render_task_block(task: dict[str, Any]) -> str:
    return json.dumps(task, indent=2, ensure_ascii=False, sort_keys=True)


def build_prompt(
    contract_text: str,
    task: dict[str, Any],
    skill_texts: list[str],
    extra_instructions: str | None = None,
) -> str:
    parts: list[str] = []

    parts.append("SYSTEM CONTRACT")
    parts.append(contract_text.strip())
    parts.append("")

    if skill_texts:
        parts.append("ACTIVE SKILLS")
        for idx, text in enumerate(skill_texts, start=1):
            parts.append(f"[SKILL {idx}]")
            parts.append(text.strip())
            parts.append("")
    else:
        parts.append("ACTIVE SKILLS")
        parts.append("None supplied.")
        parts.append("")

    if extra_instructions:
        parts.append("EXECUTION DIRECTIVES")
        parts.append(extra_instructions.strip())
        parts.append("")

    parts.append("TASK PAYLOAD")
    parts.append(render_task_block(task))
    parts.append("")
    parts.append("EXECUTION REQUIREMENTS")
    parts.append(
        "\n".join(
            [
                "- Execute only the supplied task.",
                "- Follow the contract exactly.",
                "- Use fail-closed behavior if required.",
                "- Do not add prose before STATUS.",
                "- Return output in the exact output contract shape.",
            ]
        )
    )

    return "\n".join(parts).strip() + "\n"


def run_external_executor(command: str, prompt: str) -> tuple[int, str, str]:
    cmd = shlex.split(command)
    process = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
    )
    return process.returncode, process.stdout, process.stderr


def load_allowed_failure_codes(failure_codes_path: Path | None) -> set[str]:
    if failure_codes_path is None:
        return set(DEFAULT_ALLOWED_FAILURE_CODES)

    text = read_text(failure_codes_path)
    found = set(re.findall(r"(?m)^###\s+([A-Z_]+)\s*$", text))
    if found:
        return found

    bullet_found = set(re.findall(r"(?m)^-\s+([A-Z_]+)\s*$", text))
    if bullet_found:
        return bullet_found

    return set(DEFAULT_ALLOWED_FAILURE_CODES)


def validate_output_text(
    output_text: str,
    allowed_failure_codes: set[str],
) -> list[str]:
    errors: list[str] = []

    if not output_text.startswith("STATUS: "):
        errors.append("Output must begin with 'STATUS: '")
        return errors

    first_line = output_text.splitlines()[0].strip()
    if first_line not in {"STATUS: SUCCESS", "STATUS: FAIL_CLOSED"}:
        errors.append("First line must be exactly 'STATUS: SUCCESS' or 'STATUS: FAIL_CLOSED'")

    if first_line == "STATUS: SUCCESS":
        if "\n\nOUTPUT:\n" not in output_text:
            errors.append("Success output must contain an OUTPUT section")
    elif first_line == "STATUS: FAIL_CLOSED":
        reason_match = re.search(r"(?m)^REASON:\s+([A-Z_]+)\s*$", output_text)
        if not reason_match:
            errors.append("Fail-closed output must contain a REASON line")
        else:
            reason = reason_match.group(1)
            if reason not in allowed_failure_codes:
                errors.append(f"Unrecognized failure code: {reason}")

        if not re.search(r"(?m)^DETAIL:\s*$", output_text):
            errors.append("Fail-closed output must contain a DETAIL header")

    abs_path_patterns = [
        r"(?i)\b[A-Z]:\\[^\s]+",   # Windows absolute path
        r"(?<!\.)/(home|Users|var|tmp|opt|etc)/[^\s]+",  # common Unix absolute paths
    ]
    for pattern in abs_path_patterns:
        if re.search(pattern, output_text):
            errors.append("Output appears to contain a non-portable absolute path")
            break

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute a governed Claude task with contract, skills, and validation."
    )
    parser.add_argument("--contract", required=True, help="Path to CLAUDE.md")
    parser.add_argument("--task", required=True, help="Path to task YAML or JSON")
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        help="Path to a skill file. May be specified multiple times.",
    )
    parser.add_argument(
        "--failure-codes",
        default=None,
        help="Optional path to claude-failure-codes.md",
    )
    parser.add_argument(
        "--prompt-out",
        required=True,
        help="Path to write the assembled prompt",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the executor output",
    )
    parser.add_argument(
        "--stderr-out",
        default=None,
        help="Optional path to write executor stderr when --exec is used",
    )
    parser.add_argument(
        "--exec",
        dest="exec_cmd",
        default=None,
        help="Optional external command used to execute the prompt, e.g. 'claude -p'",
    )
    parser.add_argument(
        "--extra-instructions",
        default=None,
        help="Optional extra execution directives to append to the prompt",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when no external executor is supplied.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    contract_path = Path(args.contract)
    task_path = Path(args.task)
    skill_paths = [Path(p) for p in args.skill]
    prompt_out_path = Path(args.prompt_out)
    output_path = Path(args.output)
    failure_codes_path = Path(args.failure_codes) if args.failure_codes else None
    stderr_out_path = Path(args.stderr_out) if args.stderr_out else None

    try:
        contract_text = read_text(contract_path)
        task = load_yaml_or_json(task_path)
        skill_texts = [read_text(p) for p in skill_paths]
    except Exception as exc:
        print(f"Invocation error: {exc}", file=sys.stderr)
        return 2

    task_errors = validate_task_schema(task)
    if task_errors:
        for err in task_errors:
            print(f"Task validation error: {err}", file=sys.stderr)
        return 2

    prompt = build_prompt(
        contract_text=contract_text,
        task=task,
        skill_texts=skill_texts,
        extra_instructions=args.extra_instructions,
    )
    write_text(prompt_out_path, prompt)

    if not args.exec_cmd:
        if args.strict:
            print("No external executor supplied and --strict is enabled.", file=sys.stderr)
            return 2

        placeholder = (
            "STATUS: FAIL_CLOSED\n"
            "REASON: AUTHORIZATION_MISSING\n"
            "DETAIL:\n"
            "No external Claude executor was supplied via --exec.\n"
        )
        write_text(output_path, placeholder)
        print(f"Wrote prompt to {prompt_out_path}")
        print(f"Wrote placeholder fail-closed output to {output_path}")
        return 0

    rc, stdout, stderr = run_external_executor(args.exec_cmd, prompt)
    write_text(output_path, stdout)
    if stderr_out_path is not None:
        write_text(stderr_out_path, stderr)

    if rc != 0:
        print(f"External executor failed with code {rc}", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        return 1

    allowed_failure_codes = load_allowed_failure_codes(failure_codes_path)
    output_errors = validate_output_text(stdout, allowed_failure_codes)
    if output_errors:
        for err in output_errors:
            print(f"Output validation error: {err}", file=sys.stderr)
        return 1

    print(f"Prompt written to: {prompt_out_path}")
    print(f"Output written to: {output_path}")
    if stderr_out_path is not None:
        print(f"Stderr written to: {stderr_out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
