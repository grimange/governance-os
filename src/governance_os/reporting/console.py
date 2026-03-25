"""Console reporting for governance-os.

Produces concise human-readable summaries of result objects.
Uses plain text with no terminal-specific escape codes so output
is safe to redirect or capture.
"""

from __future__ import annotations

from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.status import StatusResult


def format_scan(result: ScanResult) -> str:
    lines = [f"Found {len(result.pipelines)} pipeline(s) in {result.root}"]
    for p in result.pipelines:
        lines.append(f"  [{p.numeric_id}] {p.slug}  stage={p.stage or '?'}")
    if result.parse_errors:
        lines.append(f"\n{len(result.parse_errors)} parse error(s):")
        for e in result.parse_errors:
            lines.append(f"  [{e.code}] {e.message}")
    return "\n".join(lines)


def format_verify(result: VerifyResult) -> str:
    if result.passed:
        return f"OK — {len(result.pipelines)} pipeline(s) verified, no errors."
    lines = [
        f"FAIL — {result.error_count} error(s) across {len(result.pipelines)} pipeline(s)."
    ]
    for issue in result.issues:
        lines.append(f"  [{issue.severity.value.upper()}] [{issue.code}] {issue.message}")
    return "\n".join(lines)


def format_status(result: StatusResult) -> str:
    if not result.records:
        return "No pipelines found."
    lines: list[str] = []
    for record in result.records:
        reason_str = f" — {record.reasons[0]}" if record.reasons else ""
        lines.append(
            f"  [{record.pipeline_id}] {record.slug}  {record.status.value}{reason_str}"
        )
    return "\n".join(lines)


def format_portability(result: PortabilityResult) -> str:
    if result.passed:
        return "OK — no portability issues found."
    lines = [f"{len(result.issues)} portability issue(s):"]
    for issue in result.issues:
        lines.append(f"  [{issue.code}] {issue.message}")
    return "\n".join(lines)
