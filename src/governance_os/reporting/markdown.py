"""Markdown reporting for governance-os.

Produces diff-friendly, predictable markdown summaries of result objects.
Output contains no ANSI escape codes and can be written to files.
"""

from __future__ import annotations

from pathlib import Path

from governance_os.audit.core import AuditResult
from governance_os.authority.core import AuthorityResult
from governance_os.discovery.candidates import CandidateResult
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.status import PipelineStatus, StatusResult
from governance_os.preflight.core import PreflightResult
from governance_os.registry.core import RegistryResult
from governance_os.skills.core import SkillsResult


def _issue_table_rows(issues: list) -> list[str]:
    rows: list[str] = []
    for i in issues:
        path_str = str(i.path) if i.path else ""
        rows.append(f"| {i.severity.value} | `{i.code}` | {i.message} | {path_str} |")
    return rows


def scan_report(result: ScanResult) -> str:
    lines: list[str] = [
        "# Scan Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Pipelines found:** {len(result.pipelines)}  ",
        f"**Parse errors:** {len(result.parse_errors)}",
        "",
    ]

    if result.pipelines:
        lines += [
            "## Pipelines",
            "",
            "| ID | Slug | Stage |",
            "|---|---|---|",
        ]
        for p in result.pipelines:
            lines.append(f"| {p.numeric_id} | {p.slug} | {p.stage or '—'} |")
        lines.append("")

    if result.parse_errors:
        lines += [
            "## Parse Errors",
            "",
            "| Severity | Code | Message | Path |",
            "|---|---|---|---|",
        ]
        lines += _issue_table_rows(result.parse_errors)
        lines.append("")

    return "\n".join(lines)


def verify_report(result: VerifyResult) -> str:
    status_str = "PASSED" if result.passed else "FAILED"
    lines: list[str] = [
        "# Verify Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Status:** {status_str}  ",
        f"**Pipelines:** {len(result.pipelines)}  ",
        f"**Errors:** {result.error_count}",
        "",
    ]

    if result.issues:
        lines += [
            "## Issues",
            "",
            "| Severity | Code | Message | Path |",
            "|---|---|---|---|",
        ]
        lines += _issue_table_rows(result.issues)
        lines.append("")

    return "\n".join(lines)


def status_report(result: StatusResult) -> str:
    lines: list[str] = [
        "# Status Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Pipelines:** {len(result.records)}",
        "",
    ]

    if result.records:
        lines += [
            "## Pipeline Readiness",
            "",
            "| ID | Slug | Status | Reason |",
            "|---|---|---|---|",
        ]
        for r in result.records:
            reason = r.reasons[0] if r.reasons else ""
            lines.append(f"| {r.pipeline_id} | {r.slug} | {r.status.value} | {reason} |")
        lines.append("")

    summary_parts = []
    for s in PipelineStatus:
        count = len(result.by_status(s))
        if count:
            summary_parts.append(f"{s.value}: {count}")
    if summary_parts:
        lines += ["## Summary", "", ", ".join(summary_parts), ""]

    return "\n".join(lines)


def portability_report(result: PortabilityResult) -> str:
    status_str = "PASSED" if result.passed else "FAILED"
    lines: list[str] = [
        "# Portability Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Status:** {status_str}  ",
        f"**Issues:** {len(result.issues)}",
        "",
    ]

    if result.issues:
        lines += [
            "## Issues",
            "",
            "| Severity | Code | Message | Path |",
            "|---|---|---|---|",
        ]
        lines += _issue_table_rows(result.issues)
        lines.append("")

    return "\n".join(lines)


def registry_report(result: RegistryResult) -> str:
    status_str = "PASSED" if result.passed else "FAILED"
    lines: list[str] = [
        "# Registry Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Status:** {status_str}  ",
        f"**Entries:** {result.entry_count}",
        "",
    ]

    if result.entries:
        lines += [
            "## Registry Entries",
            "",
            "| ID | Slug | Title | Stage | Outputs |",
            "|---|---|---|---|---|",
        ]
        for e in result.entries:
            lines.append(f"| {e.pipeline_id} | {e.slug} | {e.title or '—'} | {e.stage or '—'} | {e.outputs_count} |")
        lines.append("")

    if result.issues:
        lines += [
            "## Issues",
            "",
            "| Severity | Code | Message |",
            "|---|---|---|",
        ]
        for i in result.issues:
            lines.append(f"| {i.severity.value} | `{i.code}` | {i.message} |")
        lines.append("")

    return "\n".join(lines)


def preflight_report(result: PreflightResult) -> str:
    status_str = "PASSED" if result.passed else "FAILED"
    lines: list[str] = [
        "# Preflight Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Status:** {status_str}  ",
        f"**Checks:** {', '.join(result.checks)}  ",
        f"**Errors:** {result.error_count}  ",
        f"**Warnings:** {result.warning_count}",
        "",
    ]

    if result.issues:
        lines += [
            "## Issues",
            "",
            "| Severity | Code | Message |",
            "|---|---|---|",
        ]
        for i in result.issues:
            lines.append(f"| {i.severity.value} | `{i.code}` | {i.message} |")
        lines.append("")

    return "\n".join(lines)


def audit_report(result: AuditResult) -> str:
    status_str = "PASSED" if result.passed else "FAILED"
    lines: list[str] = [
        f"# Audit Report — {result.mode.title()}",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Status:** {status_str}  ",
        f"**Findings:** {result.finding_count}",
        "",
    ]

    if result.findings:
        lines += [
            "## Findings",
            "",
            "| Severity | Code | Message |",
            "|---|---|---|",
        ]
        for f in result.findings:
            lines.append(f"| {f.severity.value} | `{f.code}` | {f.message} |")
        lines.append("")

    return "\n".join(lines)


def authority_report(result: AuthorityResult) -> str:
    status_str = "PASSED" if result.passed else "FAILED"
    lines: list[str] = [
        "# Authority Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Status:** {status_str}  ",
        f"**Issues:** {result.issue_count}",
        "",
    ]

    if result.issues:
        lines += [
            "## Issues",
            "",
            "| Severity | Code | Message |",
            "|---|---|---|",
        ]
        for i in result.issues:
            lines.append(f"| {i.severity.value} | `{i.code}` | {i.message} |")
        lines.append("")

    return "\n".join(lines)


def candidates_report(result: CandidateResult) -> str:
    lines: list[str] = [
        "# Contract Candidate Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Candidates found:** {result.candidate_count}",
        "",
    ]

    if result.candidates:
        lines += [
            "## Candidates",
            "",
            "| Suggested ID | Path | Confidence | Reason |",
            "|---|---|---|---|",
        ]
        for c in result.candidates:
            try:
                rel = c.path.relative_to(result.root)
            except ValueError:
                rel = c.path
            lines.append(f"| {c.suggested_id or '—'} | `{rel}` | {c.confidence} | {c.reason} |")
        lines.append("")
    else:
        lines.append("No contract candidates found.")
        lines.append("")

    return "\n".join(lines)


def skills_report(result: SkillsResult) -> str:
    status_str = "PASSED" if result.passed else "FAILED"
    lines: list[str] = [
        "# Skills Report",
        "",
        f"**Root:** `{result.root}`  ",
        f"**Status:** {status_str}  ",
        f"**Skills found:** {result.skill_count}",
        "",
    ]

    if result.entries:
        lines += [
            "## Skills",
            "",
            "| ID | Name | Description |",
            "|---|---|---|",
        ]
        for e in result.entries:
            lines.append(f"| `{e.skill_id}` | {e.name} | {e.description or '—'} |")
        lines.append("")

    if result.issues:
        lines += [
            "## Issues",
            "",
            "| Severity | Code | Message |",
            "|---|---|---|",
        ]
        for i in result.issues:
            lines.append(f"| {i.severity.value} | `{i.code}` | {i.message} |")
        lines.append("")

    return "\n".join(lines)


def write_report(content: str, path: Path) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
