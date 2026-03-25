"""Console reporting for governance-os.

Produces concise human-readable summaries of result objects.
Uses plain text with no terminal-specific escape codes so output
is safe to redirect or capture.
"""

from __future__ import annotations

from governance_os.audit.core import AuditResult
from governance_os.authority.core import AuthorityResult
from governance_os.discovery.candidates import CandidateResult
from governance_os.models.result import PortabilityResult, ScanResult, VerifyResult
from governance_os.models.score import ScoreResult
from governance_os.models.status import StatusResult
from governance_os.preflight.core import PreflightResult
from governance_os.registry.core import RegistryResult
from governance_os.skills.core import SkillsResult


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
    lines = [f"FAIL — {result.error_count} error(s) across {len(result.pipelines)} pipeline(s)."]
    for issue in result.issues:
        lines.append(f"  [{issue.severity.value.upper()}] [{issue.code}] {issue.message}")
    return "\n".join(lines)


def format_status(result: StatusResult) -> str:
    if not result.records:
        return "No pipelines found."
    lines: list[str] = []
    for record in result.records:
        lines.append(f"  [{record.pipeline_id}] {record.slug}  {record.status.value}")
        for reason in record.reasons:
            lines.append(f"    — {reason}")
    return "\n".join(lines)


def format_portability(result: PortabilityResult) -> str:
    if result.passed:
        return "OK — no portability issues found."
    lines = [f"{len(result.issues)} portability issue(s):"]
    for issue in result.issues:
        lines.append(f"  [{issue.code}] {issue.message}")
    return "\n".join(lines)


def format_registry(result: RegistryResult) -> str:
    status = "OK" if result.passed else "FAIL"
    lines = [f"{status} — {result.entry_count} pipeline(s) in registry"]
    for e in result.entries:
        lines.append(
            f"  [{e.pipeline_id}] {e.slug}  stage={e.stage or '?'}  outputs={e.outputs_count}"
        )
    if result.issues:
        lines.append(f"\n{len(result.issues)} issue(s):")
        for i in result.issues:
            lines.append(f"  [{i.severity.value.upper()}] [{i.code}] {i.message}")
    return "\n".join(lines)


def format_preflight(result: PreflightResult) -> str:
    if result.passed:
        checks_str = ", ".join(result.checks)
        return f"OK — preflight passed. Checks: {checks_str}"
    lines = [
        f"FAIL — {result.error_count} error(s), {result.warning_count} warning(s).",
        f"  Checks run: {', '.join(result.checks)}",
    ]
    for issue in result.issues:
        if issue.severity.value == "error":
            lines.append(f"  [ERROR] [{issue.code}] {issue.message}")
    warnings = [i for i in result.issues if i.severity.value == "warning"]
    if warnings:
        lines.append(f"  {len(warnings)} warning(s) — run with --json for full details.")
    return "\n".join(lines)


def format_audit(result: AuditResult) -> str:
    status = "OK" if result.passed else "FAIL"
    lines = [f"{status} — audit/{result.mode}: {result.finding_count} finding(s)"]
    for f in result.findings:
        sev = f.severity.value.upper()
        lines.append(f"  [{sev}] [{f.code}] {f.message}")
    return "\n".join(lines)


def format_authority(result: AuthorityResult) -> str:
    if result.passed:
        return "OK — authority checks passed."
    lines = [f"FAIL — {result.issue_count} authority issue(s):"]
    for i in result.issues:
        lines.append(f"  [{i.severity.value.upper()}] [{i.code}] {i.message}")
    return "\n".join(lines)


def format_candidates(result: CandidateResult) -> str:
    if not result.candidates:
        return "No contract candidates found."
    lines = [f"Found {result.candidate_count} contract candidate(s):"]
    for c in result.candidates:
        try:
            rel = c.path.relative_to(result.root)
        except ValueError:
            rel = c.path
        id_str = f"[{c.suggested_id}]" if c.suggested_id else "[?]"
        lines.append(f"  {id_str} {rel}  confidence={c.confidence}")
        lines.append(f"    {c.reason}")
    return "\n".join(lines)


def format_score(result: ScoreResult, explain: bool = False) -> str:
    lines = [f"Score: {result.overall_score}/100  Grade: {result.grade}"]

    for c in result.categories:
        ded = f"  ({'; '.join(c.deductions)})" if c.deductions else ""
        lines.append(f"  {c.name}: {c.score}/100{ded}")

    if explain:
        lines += ["", f"Formula: {result.formula_explanation}"]

    if result.derived_insights:
        lines.append(f"\n{len(result.derived_insights)} derived insight(s):")
        for i in result.derived_insights:
            lines.append(f"  [{i.priority.upper()}] {i.title}")
            lines.append(f"    {i.explanation}")

    high = [f for f in result.prioritized_findings if f.priority == "high"]
    medium = [f for f in result.prioritized_findings if f.priority == "medium"]
    low = [f for f in result.prioritized_findings if f.priority == "low"]

    if result.prioritized_findings:
        lines.append(
            f"\nFindings: {len(high)} high, {len(medium)} medium, {len(low)} low"
        )
        for f in result.prioritized_findings:
            suggestion = f"  -> {f.suggestion}" if f.suggestion else ""
            lines.append(f"  [{f.priority.upper()}] [{f.code}] {f.message}{suggestion}")

    if result.delta:
        lines.append("\nDelta vs previous:")
        for d in result.delta:
            sign = "+" if d.change > 0 else ""
            lines.append(
                f"  {d.category}: {d.previous_score} -> {d.current_score} ({sign}{d.change})"
            )

    return "\n".join(lines)


def format_skills(result: SkillsResult) -> str:
    status = "OK" if result.passed else "FAIL"
    lines = [f"{status} — {result.skill_count} skill(s) found"]
    for e in result.entries:
        lines.append(f"  [{e.skill_id}] {e.name}")
    if result.issues:
        lines.append(f"\n{len(result.issues)} issue(s):")
        for i in result.issues:
            lines.append(f"  [{i.severity.value.upper()}] [{i.code}] {i.message}")
    return "\n".join(lines)
