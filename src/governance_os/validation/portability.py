"""Portability scan for governance-os.

Detects non-portable path usage in pipeline output declarations so
governance contracts remain reusable across environments.

All checks are read-only and return structured diagnostics.
"""

from __future__ import annotations

import re

from governance_os.models.issue import Issue, Severity
from governance_os.models.pipeline import Pipeline

# Unix absolute path: starts with /
_UNIX_ABSOLUTE = re.compile(r"^/")

# Windows drive path: C:\ or C:/
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[/\\]")

# Path traversal: contains ../ or ..\ segments
_PATH_TRAVERSAL = re.compile(r"(^|[/\\])\.\.([/\\]|$)")

# Home-directory expansion shortcut
_HOME_TILDE = re.compile(r"^~")


def _check_output(
    output: str,
    pipeline: Pipeline,
) -> list[Issue]:
    """Check a single output path declaration for portability problems."""
    issues: list[Issue] = []
    pid = pipeline.numeric_id
    path = pipeline.path
    stripped = output.strip()

    if not stripped:
        return issues

    if _UNIX_ABSOLUTE.match(stripped):
        issues.append(
            Issue(
                code="ABSOLUTE_PATH",
                severity=Severity.ERROR,
                message=f"Output '{stripped}' is an absolute Unix path.",
                path=path,
                pipeline_id=pid,
                suggestion="Use a repo-root-relative path instead (e.g. 'artifacts/foo.json').",
            )
        )

    elif _WINDOWS_DRIVE.match(stripped):
        issues.append(
            Issue(
                code="WINDOWS_DRIVE_PATH",
                severity=Severity.ERROR,
                message=f"Output '{stripped}' contains a Windows drive letter path.",
                path=path,
                pipeline_id=pid,
                suggestion="Use a repo-root-relative path instead.",
            )
        )

    elif _HOME_TILDE.match(stripped):
        issues.append(
            Issue(
                code="HOME_RELATIVE_PATH",
                severity=Severity.ERROR,
                message=f"Output '{stripped}' uses a home-directory (~) reference.",
                path=path,
                pipeline_id=pid,
                suggestion="Use a repo-root-relative path instead.",
            )
        )

    elif _PATH_TRAVERSAL.search(stripped):
        issues.append(
            Issue(
                code="PATH_TRAVERSAL",
                severity=Severity.ERROR,
                message=f"Output '{stripped}' uses '..' which may escape the repo root.",
                path=path,
                pipeline_id=pid,
                suggestion="Remove '..' segments and use explicit repo-root-relative paths.",
            )
        )

    return issues


def scan_pipeline(pipeline: Pipeline) -> list[Issue]:
    """Scan a single pipeline's output declarations for portability issues.

    Args:
        pipeline: Typed pipeline model to scan.

    Returns:
        List of Issue records. Empty means no portability problems found.
    """
    issues: list[Issue] = []
    for output in pipeline.outputs:
        issues.extend(_check_output(output, pipeline))
    return issues


def scan_pipelines(pipelines: list[Pipeline]) -> list[Issue]:
    """Scan all pipelines for portability issues.

    Args:
        pipelines: Full pipeline inventory.

    Returns:
        Flat list of all portability Issue records.
    """
    issues: list[Issue] = []
    for pipeline in pipelines:
        issues.extend(scan_pipeline(pipeline))
    return issues
