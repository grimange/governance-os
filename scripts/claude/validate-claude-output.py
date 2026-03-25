#!/usr/bin/env python3
"""
validate-claude-output.py

Strict validator for Governance OS Claude outputs.

This script validates a Claude response against the Governance OS output
contract and optionally enforces required markdown sections for SUCCESS
outputs.

Typical usage:

    python scripts/claude/validate-claude-output.py \
      --input artifacts/claude/output.txt \
      --failure-codes docs/contracts/claude-failure-codes.md

With required sections:

    python scripts/claude/validate-claude-output.py \
      --input output.txt \
      --failure-codes docs/contracts/claude-failure-codes.md \
      --require-section "## Status" \
      --require-section "## Findings" \
      --require-section "## Conclusion"

Exit codes:
    0 = valid
    1 = invalid output
    2 = invocation error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


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


def load_allowed_failure_codes(path: Path | None) -> set[str]:
    if path is None:
        return set(DEFAULT_ALLOWED_FAILURE_CODES)

    text = read_text(path)
    heading_matches = set(re.findall(r"(?m)^###\s+([A-Z_]+)\s*$", text))
    if heading_matches:
        return heading_matches

    bullet_matches = set(re.findall(r"(?m)^-\s+([A-Z_]+)\s*$", text))
    if bullet_matches:
        return bullet_matches

    return set(DEFAULT_ALLOWED_FAILURE_CODES)


def detect_absolute_path(text: str) -> bool:
    patterns = [
        r"(?i)\b[A-Z]:\\[^\s]+",
        r"(?<!\.)/(home|Users|var|tmp|opt|etc)/[^\s]+",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def extract_success_output_block(text: str) -> str | None:
    match = re.search(r"(?s)^STATUS:\s+SUCCESS\s*\n\nOUTPUT:\n(.*)$", text)
    if match:
        return match.group(1)
    return None


def validate_success_output(
    text: str,
    required_sections: list[str],
    forbid_extra_prose: bool,
) -> list[str]:
    errors: list[str] = []

    block = extract_success_output_block(text)
    if block is None:
        errors.append("Success output must match the exact shape: STATUS, blank line, OUTPUT:")
        return errors

    if forbid_extra_prose:
        exact_match = re.fullmatch(r"(?s)STATUS:\s+SUCCESS\s*\n\nOUTPUT:\n.*", text)
        if exact_match is None:
            errors.append("Success output contains text outside the allowed STATUS/OUTPUT structure")

    for section in required_sections:
        if section not in block:
            errors.append(f"Missing required section: {section}")

    return errors


def validate_fail_closed_output(text: str, allowed_failure_codes: set[str]) -> list[str]:
    errors: list[str] = []

    first = text.splitlines()[0] if text.splitlines() else ""
    status_match = re.match(r"^STATUS:\s+FAIL_CLOSED\s*$", first)
    if not status_match:
        errors.append("First line must be exactly: STATUS: FAIL_CLOSED")
        return errors

    reason_match = re.search(r"(?m)^REASON:\s+([A-Z_]+)\s*$", text)
    if not reason_match:
        errors.append("Fail-closed output must include a REASON line")
    else:
        reason = reason_match.group(1)
        if reason not in allowed_failure_codes:
            errors.append(f"Unrecognized failure code: {reason}")

    detail_header = re.search(r"(?m)^DETAIL:\s*$", text)
    if not detail_header:
        errors.append("Fail-closed output must include a DETAIL header")
    else:
        detail_match = re.search(r"(?s)^DETAIL:\s*\n(.+)$", text[detail_header.start():])
        if detail_match is None:
            errors.append("DETAIL section must contain a grounded explanation")

    return errors


def validate_text(
    text: str,
    allowed_failure_codes: set[str],
    required_sections: list[str],
    forbid_extra_prose: bool,
    reject_absolute_paths: bool,
) -> list[str]:
    errors: list[str] = []

    if not text.startswith("STATUS: "):
        errors.append("Output must begin with 'STATUS: '")
        return errors

    first_line = text.splitlines()[0].strip()
    if first_line == "STATUS: SUCCESS":
        errors.extend(validate_success_output(text, required_sections, forbid_extra_prose))
    elif first_line == "STATUS: FAIL_CLOSED":
        errors.extend(validate_fail_closed_output(text, allowed_failure_codes))
    else:
        errors.append("First line must be exactly 'STATUS: SUCCESS' or 'STATUS: FAIL_CLOSED'")

    if reject_absolute_paths and detect_absolute_path(text):
        errors.append("Output appears to contain a non-portable absolute path")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Claude output against Governance OS output contract."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the Claude output file to validate",
    )
    parser.add_argument(
        "--failure-codes",
        default=None,
        help="Optional path to claude-failure-codes.md",
    )
    parser.add_argument(
        "--require-section",
        action="append",
        default=[],
        help="Require a markdown section inside the OUTPUT block for SUCCESS outputs",
    )
    parser.add_argument(
        "--allow-extra-prose",
        action="store_true",
        help="Allow extra prose outside the STATUS/OUTPUT structure for SUCCESS outputs",
    )
    parser.add_argument(
        "--allow-absolute-paths",
        action="store_true",
        help="Allow absolute paths in the output text",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    failure_codes_path = Path(args.failure_codes) if args.failure_codes else None

    try:
        text = read_text(input_path)
        allowed_failure_codes = load_allowed_failure_codes(failure_codes_path)
    except Exception as exc:
        print(f"Invocation error: {exc}", file=sys.stderr)
        return 2

    errors = validate_text(
        text=text,
        allowed_failure_codes=allowed_failure_codes,
        required_sections=args.require_section,
        forbid_extra_prose=not args.allow_extra_prose,
        reject_absolute_paths=not args.allow_absolute_paths,
    )

    if errors:
        for err in errors:
            print(f"Validation error: {err}", file=sys.stderr)
        return 1

    print("VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
