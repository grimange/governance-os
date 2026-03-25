"""Scaffold logic for governance-os repo initialization."""

from dataclasses import dataclass, field
from enum import StrEnum
from importlib.resources import files
from pathlib import Path

from governance_os.models.issue import Issue, Severity


def _template(name: str) -> str:
    return files("governance_os.templates").joinpath(name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Init levels and profiles
# ---------------------------------------------------------------------------


class InitLevel(StrEnum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    GOVERNED = "governed"


class InitProfile(StrEnum):
    GENERIC = "generic"
    CODEX = "codex"


# Valid template names for the --template flag (subset of InitLevel, excludes "standard")
VALID_TEMPLATES = frozenset({"minimal", "governed"})

# ---------------------------------------------------------------------------
# Example pipeline template
# ---------------------------------------------------------------------------

_EXAMPLE_PIPELINE = """\
# 001 — Example Pipeline

Stage: establish

Purpose:
Describe what this pipeline does and the outcome it produces.

Depends on:
- none

Inputs:
- none

Outputs:
- artifacts/example.json

Implementation Notes:
Replace this contract with your first real pipeline.

Success Criteria:
- Output artifact exists and is non-empty

Out of Scope:
- Production deployment
"""

_MINIMAL_PIPELINE = """\
# 001 — Bootstrap

Stage: establish

Purpose:
Initial pipeline contract.

Depends on:
- none

Outputs:
- artifacts/bootstrap.json

Success Criteria:
- Outputs produced
"""


# ---------------------------------------------------------------------------
# Codex session template (inline, so it doesn't depend on template load at init)
# ---------------------------------------------------------------------------

_CODEX_SESSION_TEMPLATE = """\
# Codex Session Contract

**Session ID:** <!-- fill in session id -->
**Date:** <!-- fill in date -->
**Operator:** <!-- fill in operator -->

## Objective

<!-- Describe the session objective -->

## Scope

<!-- Define what is in scope for this session -->

## Authorized Actions

- <!-- List authorized actions -->

## Expected Outputs

- <!-- List expected deliverables -->

## Session Status

- [ ] Initiated
- [ ] In Progress
- [ ] Completed
- [ ] Verified
"""

_AGENTS_MD_TEMPLATE = """\
# AGENTS.md — Codex Governance Instructions

This repository uses governance-os for pipeline contract management.

## Governance Structure

- Pipeline contracts: `governance/pipelines/`
- Governance config: `governance.yaml`
- Session contracts: `governance/sessions/`

## Rules

1. Do not modify pipeline contracts without explicit authorization.
2. All pipeline outputs must be declared in the contract.
3. Dependencies must reference numeric pipeline IDs, not file paths.
4. Run `govos preflight` before making governance-affecting changes.

## Quick Reference

```
govos scan             # discover all pipeline contracts
govos verify           # validate contracts and dependency graph
govos preflight        # fail-closed readiness gate
govos score            # governance health score
govos profile validate # check repo conforms to active profile
```
"""

# .codex/config.toml — written for all codex templates
_CODEX_CONFIG_TOML = """\
# .codex/config.toml — Codex governance profile configuration

[governance]
profile = "codex"
contracts = "governance/pipelines"
artifacts = "artifacts"

[preflight]
enabled = true
"""

# governance/skills/govos-preflight.skill.md — written for codex:governed only
_CODEX_PREFLIGHT_SKILL = """\
# Skill: govos-preflight

**Trigger:** Before governance-affecting changes

## Steps

1. Run `govos preflight` at repo root.
2. Resolve all ERROR issues before continuing.
3. Document preflight status in session contract if applicable.

## Pass Criteria

- `govos preflight` exits 0
- No unresolved ERROR issues
"""

_DOCTRINE_TEMPLATE = """\
# Governance Doctrine

**Version:** 1.0.0

## Principles

1. All pipeline stages must have formal contracts.
2. Contracts must declare explicit outputs and success criteria.
3. Dependencies must reference numeric ids.
4. Output paths must be repo-relative.
"""


# ---------------------------------------------------------------------------
# governance.yaml content generation
# ---------------------------------------------------------------------------


def _governance_yaml(profile: str, governed: bool) -> str:
    """Generate governance.yaml content for the given profile and structure level.

    Args:
        profile: Profile identifier ("generic" or "codex").
        governed: True for governed-level content (authority, registry, audit sections).

    Returns:
        YAML string suitable for writing to governance.yaml.
    """
    lines = [
        "# governance-os configuration",
        "pipelines_dir: governance/pipelines",
        'contracts_glob: "**/*.md"',
        f"profile: {profile}",
    ]
    if governed:
        lines += [
            "",
            "authority:",
            "  required_roots:",
            "    - governance.yaml",
            "    - governance/pipelines/",
            "",
            "registry:",
            "  snapshot_path: artifacts/governance/registry.json",
            "",
            "audit:",
            "  enabled: true",
        ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Scaffold result
# ---------------------------------------------------------------------------


@dataclass
class ScaffoldResult:
    """Result of a scaffold operation."""

    root: Path
    level: str = "standard"
    profile: str = "generic"
    template: str = ""
    created_dirs: list[Path] = field(default_factory=list)
    created_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core scaffolding
# ---------------------------------------------------------------------------


def _create_dir(result: ScaffoldResult, d: Path) -> None:
    if not d.exists():
        d.mkdir(parents=True)
        result.created_dirs.append(d)


def _write_file(result: ScaffoldResult, path: Path, content: str) -> None:
    if path.exists():
        result.skipped_files.append(path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        result.created_files.append(path)


def init_repo(
    root: Path,
    level: str = "standard",
    profile: str = "generic",
    with_doctrine: bool = False,
    template: str | None = None,
) -> ScaffoldResult:
    """Initialize a governance-os repo at *root*.

    Creates the standard directory layout and default files.
    Existing files are never overwritten.

    Args:
        root: Target directory (created if it does not exist).
        level: Governance maturity level — "minimal", "standard", or "governed".
            Legacy parameter; use *template* for new code.
        profile: Optional profile — "generic" (default) or "codex".
        with_doctrine: If True, scaffold an optional doctrine file.
        template: Template name — "minimal" or "governed". Takes precedence over
            *level* when provided. Invalid template values raise ValueError.

    Returns:
        ScaffoldResult describing what was created or skipped.

    Raises:
        ValueError: If *template* is given but not in VALID_TEMPLATES.
    """
    # Resolve effective level: template takes precedence over level
    if template is not None:
        if template not in VALID_TEMPLATES:
            raise ValueError(
                f"Invalid template: {template!r}. "
                f"Supported templates: {', '.join(sorted(VALID_TEMPLATES))}"
            )
        effective_level = template
    else:
        effective_level = level

    try:
        init_level = InitLevel(effective_level)
    except ValueError:
        init_level = InitLevel.STANDARD

    try:
        init_profile = InitProfile(profile)
    except ValueError:
        init_profile = InitProfile.GENERIC

    effective_template = template or effective_level

    result = ScaffoldResult(
        root=root,
        level=init_level.value,
        profile=init_profile.value,
        template=effective_template,
    )

    # Decide governance.yaml content upfront (profile + governed flag)
    is_governed = init_level == InitLevel.GOVERNED
    gov_yaml_content = _governance_yaml(init_profile.value, governed=is_governed)

    # ------------------------------------------------------------------
    # MINIMAL — absolute minimum governance structure
    # ------------------------------------------------------------------
    _create_dir(result, root / "governance" / "pipelines")
    _create_dir(result, root / "artifacts")
    _write_file(result, root / "governance.yaml", gov_yaml_content)
    _write_file(
        result,
        root / "governance" / "pipelines" / "001--example.md",
        _MINIMAL_PIPELINE if init_level == InitLevel.MINIMAL else _EXAMPLE_PIPELINE,
    )

    if init_level == InitLevel.MINIMAL:
        _apply_profile(result, root, init_profile, init_level)
        return result

    # ------------------------------------------------------------------
    # STANDARD — default structure (extends minimal)
    # ------------------------------------------------------------------
    _create_dir(result, root / "docs" / "governance")
    _write_file(
        result,
        root / "docs" / "governance" / "README.governance.md",
        _template("README.governance.md"),
    )

    if init_level == InitLevel.STANDARD and not with_doctrine:
        _apply_profile(result, root, init_profile, init_level)
        return result

    # ------------------------------------------------------------------
    # GOVERNED — full structure (extends standard)
    # ------------------------------------------------------------------
    _create_dir(result, root / "artifacts" / "governance")
    _create_dir(result, root / "governance" / "skills")

    _write_file(
        result,
        root / "docs" / "governance" / "README.governance.md",
        _template("README.governance.governed.md"),
    )

    # Doctrine (optional but always written for governed level; also --with-doctrine)
    if with_doctrine or init_level == InitLevel.GOVERNED:
        _create_dir(result, root / "governance" / "doctrine")
        _write_file(
            result,
            root / "governance" / "doctrine" / "doctrine.md",
            _DOCTRINE_TEMPLATE,
        )

    _apply_profile(result, root, init_profile, init_level)
    return result


def _apply_profile(
    result: ScaffoldResult,
    root: Path,
    profile: InitProfile,
    level: InitLevel,
) -> None:
    """Apply profile-specific scaffold assets.

    Args:
        result: ScaffoldResult to track created/skipped files.
        root: Repo root directory.
        profile: Active profile.
        level: Effective init level (controls which profile assets are included).
    """
    if profile == InitProfile.CODEX:
        # Always-on Codex assets (all templates)
        _create_dir(result, root / "governance" / "sessions")
        _write_file(
            result,
            root / "governance" / "sessions" / "session-template.md",
            _CODEX_SESSION_TEMPLATE,
        )
        _write_file(result, root / "AGENTS.md", _AGENTS_MD_TEMPLATE)
        _write_file(result, root / ".codex" / "config.toml", _CODEX_CONFIG_TOML)

        # Codex governed: add a concrete preflight skill
        if level == InitLevel.GOVERNED:
            _create_dir(result, root / "governance" / "skills")
            _write_file(
                result,
                root / "governance" / "skills" / "govos-preflight.skill.md",
                _CODEX_PREFLIGHT_SKILL,
            )


# ---------------------------------------------------------------------------
# Doctrine validation
# ---------------------------------------------------------------------------


def validate_doctrine(root: Path) -> list[Issue]:
    """Check that a doctrine pack exists and all files are non-empty.

    Scans governance/doctrine/ for all .md files (multi-file packs supported).
    Returns a list of Issue objects. Empty list means valid.
    """
    issues: list[Issue] = []
    doctrine_dir = root / "governance" / "doctrine"

    if not doctrine_dir.exists():
        issues.append(
            Issue(
                code="DOCTRINE_MISSING",
                severity=Severity.ERROR,
                message=f"Doctrine directory not found: {doctrine_dir}",
                path=root,
                suggestion="Create governance/doctrine/ and add at least one .md file.",
            )
        )
        return issues

    doctrine_files = sorted(doctrine_dir.glob("*.md"))
    if not doctrine_files:
        issues.append(
            Issue(
                code="DOCTRINE_MISSING",
                severity=Severity.ERROR,
                message=f"No doctrine files (.md) found in {doctrine_dir}",
                path=doctrine_dir,
                suggestion="Create at least one .md file in governance/doctrine/.",
            )
        )
        return issues

    for doc_file in doctrine_files:
        content = doc_file.read_text(encoding="utf-8").strip()
        if not content:
            issues.append(
                Issue(
                    code="DOCTRINE_EMPTY",
                    severity=Severity.WARNING,
                    message=f"Doctrine file is empty: {doc_file.name}",
                    path=doc_file,
                )
            )
        elif len(content.splitlines()) < 3:
            issues.append(
                Issue(
                    code="DOCTRINE_INCOMPLETE",
                    severity=Severity.WARNING,
                    message=f"Doctrine file appears incomplete (fewer than 3 lines): {doc_file.name}",
                    path=doc_file,
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_result(result: ScaffoldResult) -> str:
    """Return a human-readable summary of a ScaffoldResult."""
    template_label = result.template or result.level
    lines: list[str] = [
        f"Initialized governance-os repo at: {result.root}",
        f"  profile={result.profile}  template={template_label}",
    ]

    if result.created_dirs:
        lines.append("\nDirectories created:")
        for d in result.created_dirs:
            lines.append(f"  + {d.relative_to(result.root)}/")

    if result.created_files:
        lines.append("\nFiles created:")
        for f in result.created_files:
            lines.append(f"  + {f.relative_to(result.root)}")

    if result.skipped_files:
        lines.append("\nFiles skipped (already exist):")
        for f in result.skipped_files:
            lines.append(f"  ~ {f.relative_to(result.root)}")

    return "\n".join(lines)
