"""Scaffold logic for governance-os repo initialization.

Architecture
------------
Scaffold generation is split into two phases:

  1. Planning  — plan_scaffold() returns a ScaffoldPlan: a pure data object
                 describing every directory and file to create.  No I/O occurs.
  2. Execution — execute_plan() applies a ScaffoldPlan to the filesystem,
                 respecting the chosen ConflictPolicy.

Both the dry-run display (format_plan) and real execution (execute_plan) operate
on the same ScaffoldPlan object, guaranteeing they describe exactly the same
mutation.

Public API
----------
  plan_scaffold(root, profile, template, with_doctrine) -> ScaffoldPlan
  execute_plan(plan, conflict)                          -> ScaffoldResult
  validate_scaffold(root, plan)                         -> list[Issue]
  format_plan(plan, check_existing)                     -> str
  init_repo(root, ...)                                  -> ScaffoldResult
      Convenience wrapper: plan_scaffold + execute_plan in one call.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from importlib.resources import files
from pathlib import Path

from governance_os.models.issue import Issue, Severity


def _template(name: str) -> str:
    return files("governance_os.templates").joinpath(name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Init levels, profiles, and scaffold versioning
# ---------------------------------------------------------------------------


class InitLevel(StrEnum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    GOVERNED = "governed"


class InitProfile(StrEnum):
    GENERIC = "generic"
    CODEX = "codex"


# Templates exposed via the --template flag (does not include "standard",
# which is only reachable via the legacy --level flag).
VALID_TEMPLATES = frozenset({"minimal", "governed", "multi-agent"})

# All recognised template/level names accepted by plan_scaffold().
# Includes "standard" for backward-compatible callers via init_repo().
_ALL_TEMPLATES = frozenset({"minimal", "standard", "governed", "multi-agent"})

# Scaffold contract version — increment when scaffold outputs change in a way
# that existing repos may need to be updated.
SCAFFOLD_VERSION = "1"


class ConflictPolicy(StrEnum):
    """How to handle files that already exist when executing a scaffold plan."""

    SKIP = "skip"          # Leave existing files unchanged (default — safe, idempotent).
    FAIL = "fail"          # Raise FileExistsError if any planned file already exists.
    OVERWRITE = "overwrite"  # Replace existing files with the planned content.


# ---------------------------------------------------------------------------
# Example pipeline template strings
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
# Codex session template
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

_AGENTS_MD_MULTI_AGENT_TEMPLATE = """\
# AGENTS.md — Codex Governance Instructions

This repository uses governance-os for pipeline contract management with role-specialized agents.

## Governance Structure

- Pipeline contracts: `governance/pipelines/`
- Governance config: `governance.yaml`
- Session contracts: `governance/sessions/`
- Role contracts: `docs/governance/agents/`
- Workflow contract: `docs/contracts/multi-agent-workflow.md`

## Roles

See `docs/governance/agents/` for full role contracts.

| Role | Responsibilities |
|---|---|
| `planner` | Decomposes work into pipeline contracts; deposits handoff in `artifacts/governance/handoffs/` |
| `implementer` | Executes work per approved contracts; requests review in `artifacts/governance/reviews/` |
| `reviewer` | Validates outputs against contracts; records outcome in `artifacts/governance/reviews/` |

## Rules

1. Do not modify pipeline contracts without explicit authorization.
2. All pipeline outputs must be declared in the contract.
3. Dependencies must reference numeric pipeline IDs, not file paths.
4. Run `govos preflight` before making governance-affecting changes.
5. Each role must operate within its defined scope — see role contract for forbidden actions.

## Quick Reference

```
govos scan                  # discover all pipeline contracts
govos verify                # validate contracts and dependency graph
govos preflight             # fail-closed readiness gate
govos audit multi-agent     # validate multi-agent structure
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

# ---------------------------------------------------------------------------
# Multi-agent role definition templates (.codex/agents/*.toml)
# ---------------------------------------------------------------------------

_PLANNER_TOML = """\
# .codex/agents/planner.toml — Planner agent definition

[agent]
id = "planner"
role = "planner"
description = "Decomposes work into governed pipeline contracts before implementation begins."

[responsibilities]
required = [
  "Produce a task breakdown before implementation begins",
  "Ensure each task maps to a pipeline contract in governance/pipelines/",
  "Declare all inter-task dependencies",
  "Obtain explicit approval before handoff to implementer",
]

[handoff]
produces = "artifacts/governance/handoffs/"

[constraints]
forbidden = [
  "Modifying implementation files directly",
  "Bypassing governance review steps",
]
"""

_IMPLEMENTER_TOML = """\
# .codex/agents/implementer.toml — Implementer agent definition

[agent]
id = "implementer"
role = "implementer"
description = "Executes work as defined in approved pipeline contracts."

[responsibilities]
required = [
  "Execute only work declared in an approved pipeline contract",
  "Produce all declared contract outputs",
  "Run govos preflight before and after governance-affecting changes",
  "Record completion in review request artifact",
]

[handoff]
receives = "artifacts/governance/handoffs/"
produces = "artifacts/governance/reviews/"

[constraints]
forbidden = [
  "Expanding scope beyond the pipeline contract",
  "Modifying governance contracts without planner approval",
]
"""

_REVIEWER_TOML = """\
# .codex/agents/reviewer.toml — Reviewer agent definition

[agent]
id = "reviewer"
role = "reviewer"
description = "Validates that implementation outputs match the pipeline contract."

[responsibilities]
required = [
  "Verify all declared contract outputs exist and are non-empty",
  "Run govos verify and govos preflight",
  "Check that no out-of-scope changes were made",
  "Produce a review outcome record in artifacts/governance/reviews/",
]

[handoff]
receives = "artifacts/governance/reviews/"
produces = "Approval or rejection decision"

[constraints]
forbidden = [
  "Approving incomplete or non-compliant outputs",
  "Skipping govos preflight validation",
]
"""

# ---------------------------------------------------------------------------
# Multi-agent role contract templates (docs/governance/agents/*.md)
# ---------------------------------------------------------------------------

_PLANNER_CONTRACT = """\
# Role Contract: Planner

**Profile:** codex
**Role ID:** planner

## Purpose

Decompose work into governed pipeline contracts before any implementation begins.

## Responsibilities

1. Produce a task breakdown for each work unit.
2. Ensure each task maps to a pipeline contract in governance/pipelines/.
3. Declare all inter-task dependencies.
4. Obtain explicit approval before handing off to the implementer.

## Required Outputs

- Handoff record in artifacts/governance/handoffs/

## Forbidden Actions

- Modifying implementation files directly
- Bypassing governance review steps
"""

_IMPLEMENTER_CONTRACT = """\
# Role Contract: Implementer

**Profile:** codex
**Role ID:** implementer

## Purpose

Execute work as defined in approved pipeline contracts.

## Responsibilities

1. Execute only work declared in an approved pipeline contract.
2. Produce all declared contract outputs.
3. Run `govos preflight` before and after governance-affecting changes.
4. Record completion status in review request artifact.

## Required Outputs

- All outputs declared in the active pipeline contract
- Review request artifact in artifacts/governance/reviews/

## Forbidden Actions

- Expanding scope beyond the pipeline contract
- Modifying governance contracts without planner approval
"""

_REVIEWER_CONTRACT = """\
# Role Contract: Reviewer

**Profile:** codex
**Role ID:** reviewer

## Purpose

Validate that implementation outputs match the pipeline contract and governance rules.

## Responsibilities

1. Verify all declared contract outputs exist and are non-empty.
2. Run `govos verify` and `govos preflight`.
3. Check that no out-of-scope changes were made.
4. Produce a review outcome record.

## Required Outputs

- Review outcome in artifacts/governance/reviews/

## Forbidden Actions

- Approving incomplete or non-compliant outputs
- Skipping govos preflight validation
"""

# ---------------------------------------------------------------------------
# Multi-agent workflow contract (docs/contracts/multi-agent-workflow.md)
# ---------------------------------------------------------------------------

_MULTI_AGENT_WORKFLOW = """\
# Multi-Agent Workflow Contract

**Profile:** codex
**Template:** multi-agent

## Roles

| Role | ID | Responsibility |
|---|---|---|
| Planner | planner | Decomposes work into pipeline contracts |
| Implementer | implementer | Executes work per approved contracts |
| Reviewer | reviewer | Validates outputs against contracts |

## Sequence

1. **Plan** — Planner decomposes work, maps tasks to pipeline contracts, deposits handoff in artifacts/governance/handoffs/
2. **Implement** — Implementer executes work, produces declared outputs, deposits review request in artifacts/governance/reviews/
3. **Review** — Reviewer validates outputs, runs govos preflight, records outcome

## Artifacts

| Artifact | Path | Written by |
|---|---|---|
| Handoff records | artifacts/governance/handoffs/ | Planner |
| Review requests | artifacts/governance/reviews/ | Implementer |
| Review outcomes | artifacts/governance/reviews/ | Reviewer |

## Completion Criteria

- All declared pipeline outputs exist
- `govos preflight` passes
- Review outcome recorded as approved
- No out-of-scope changes present
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


def _governance_yaml(profile: str, governed: bool, template: str = "") -> str:
    """Generate governance.yaml content for the given profile and structure level.

    Args:
        profile: Profile identifier ("generic" or "codex").
        governed: True for governed-level content (authority, registry, audit sections).
        template: Template name — used to enable plugins when template="multi-agent".

    Returns:
        YAML string suitable for writing to governance.yaml.
    """
    lines = [
        "# governance-os configuration",
        "pipelines_dir: governance/pipelines",
        'contracts_glob: "**/*.md"',
        f"profile: {profile}",
    ]
    if template == "multi-agent":
        lines += [
            "",
            "enabled_plugins:",
            "  - multi_agent",
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
# Scaffold model
# ---------------------------------------------------------------------------


@dataclass
class ScaffoldFile:
    """A single file entry in a ScaffoldPlan."""

    path: Path      # Absolute path to the file to create.
    content: str    # Exact content to write.


@dataclass
class ScaffoldPlan:
    """Complete, immutable description of what govos init will create.

    Built by plan_scaffold(); applied by execute_plan(); displayed by format_plan().
    All three operations share this object, guaranteeing that dry-run output
    matches real execution.
    """

    root: Path
    profile: str
    template: str
    scaffold_version: str
    directories: list[Path] = field(default_factory=list)    # absolute paths, ordered
    files: list[ScaffoldFile] = field(default_factory=list)  # ordered, no duplicates


# ---------------------------------------------------------------------------
# Scaffold result
# ---------------------------------------------------------------------------


@dataclass
class ScaffoldResult:
    """Result of executing a scaffold plan."""

    root: Path
    level: str = "standard"
    profile: str = "generic"
    template: str = ""
    created_dirs: list[Path] = field(default_factory=list)
    created_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    overwritten_files: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core scaffold functions
# ---------------------------------------------------------------------------


def plan_scaffold(
    root: Path,
    profile: str = "generic",
    template: str = "standard",
    with_doctrine: bool = False,
) -> ScaffoldPlan:
    """Build a scaffold plan without touching the filesystem.

    This is the single source of scaffold truth. Both dry-run display and real
    filesystem execution operate on the returned plan, guaranteeing they
    describe exactly the same mutation.

    Args:
        root: Target repo root directory (need not exist yet).
        profile: Governance profile — "generic" (default) or "codex".
        template: Scaffold template — "minimal", "standard", "governed", or
            "multi-agent". "standard" is accepted here for backward-compatible
            callers; it is not exposed as a --template CLI value.
        with_doctrine: Include a doctrine file even for standard-level templates.

    Returns:
        ScaffoldPlan listing every directory and file to create.

    Raises:
        ValueError: If profile is unrecognized, template is unsupported, or
            the combination is invalid (e.g. multi-agent without codex profile).
    """
    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    try:
        init_profile = InitProfile(profile)
    except ValueError:
        valid = ", ".join(p.value for p in InitProfile)
        raise ValueError(f"Invalid profile: {profile!r}. Supported: {valid}")

    if template not in _ALL_TEMPLATES:
        raise ValueError(
            f"Invalid template: {template!r}. "
            f"Supported: {', '.join(sorted(VALID_TEMPLATES))}"
        )

    if template == "multi-agent" and init_profile != InitProfile.CODEX:
        raise ValueError(
            "The 'multi-agent' template requires --profile codex. "
            "Use: govos init --profile codex --template multi-agent"
        )

    # ------------------------------------------------------------------
    # Resolve effective level
    # ------------------------------------------------------------------
    effective_level = "governed" if template == "multi-agent" else template
    try:
        init_level = InitLevel(effective_level)
    except ValueError:
        init_level = InitLevel.STANDARD  # "standard" → STANDARD

    is_governed = init_level == InitLevel.GOVERNED
    gov_yaml = _governance_yaml(init_profile.value, governed=is_governed, template=template)

    dirs: list[Path] = []
    sfiles: list[ScaffoldFile] = []

    def add_dir(p: Path) -> None:
        dirs.append(p)

    def add_file(p: Path, content: str) -> None:
        sfiles.append(ScaffoldFile(path=p, content=content))

    # ------------------------------------------------------------------
    # MINIMAL — absolute minimum governance structure
    # ------------------------------------------------------------------
    add_dir(root / "governance" / "pipelines")
    add_dir(root / "artifacts")
    add_file(root / "governance.yaml", gov_yaml)
    add_file(
        root / "governance" / "pipelines" / "001--example.md",
        _MINIMAL_PIPELINE if init_level == InitLevel.MINIMAL else _EXAMPLE_PIPELINE,
    )

    if init_level != InitLevel.MINIMAL:
        # ------------------------------------------------------------------
        # STANDARD — extends minimal (docs directory, README)
        # ------------------------------------------------------------------
        add_dir(root / "docs" / "governance")
        # Use the governed README when the effective level is governed;
        # this avoids the original bug where the governed README was shadowed
        # by the standard README being written first.
        readme = (
            _template("README.governance.governed.md")
            if is_governed
            else _template("README.governance.md")
        )
        add_file(root / "docs" / "governance" / "README.governance.md", readme)

        if is_governed or with_doctrine:
            # ------------------------------------------------------------------
            # GOVERNED — extends standard (registry artifacts, skills, doctrine)
            # ------------------------------------------------------------------
            add_dir(root / "artifacts" / "governance")
            add_dir(root / "governance" / "skills")

            if is_governed or with_doctrine:
                add_dir(root / "governance" / "doctrine")
                add_file(root / "governance" / "doctrine" / "doctrine.md", _DOCTRINE_TEMPLATE)

    # ------------------------------------------------------------------
    # Profile-specific assets
    # ------------------------------------------------------------------
    if init_profile == InitProfile.CODEX:
        add_dir(root / "governance" / "sessions")
        add_file(
            root / "governance" / "sessions" / "session-template.md",
            _CODEX_SESSION_TEMPLATE,
        )
        agents_md = (
            _AGENTS_MD_MULTI_AGENT_TEMPLATE if template == "multi-agent" else _AGENTS_MD_TEMPLATE
        )
        add_file(root / "AGENTS.md", agents_md)
        add_file(root / ".codex" / "config.toml", _CODEX_CONFIG_TOML)

        # Preflight skill — only for governed-level repos
        if is_governed:
            add_file(
                root / "governance" / "skills" / "govos-preflight.skill.md",
                _CODEX_PREFLIGHT_SKILL,
            )

        # Multi-agent extras
        if template == "multi-agent":
            add_file(root / ".codex" / "agents" / "planner.toml", _PLANNER_TOML)
            add_file(root / ".codex" / "agents" / "implementer.toml", _IMPLEMENTER_TOML)
            add_file(root / ".codex" / "agents" / "reviewer.toml", _REVIEWER_TOML)
            add_file(
                root / "docs" / "governance" / "agents" / "planner.md", _PLANNER_CONTRACT
            )
            add_file(
                root / "docs" / "governance" / "agents" / "implementer.md",
                _IMPLEMENTER_CONTRACT,
            )
            add_file(
                root / "docs" / "governance" / "agents" / "reviewer.md", _REVIEWER_CONTRACT
            )
            add_file(
                root / "docs" / "contracts" / "multi-agent-workflow.md", _MULTI_AGENT_WORKFLOW
            )
            add_dir(root / "artifacts" / "governance" / "handoffs")
            add_dir(root / "artifacts" / "governance" / "reviews")
            add_file(root / "artifacts" / "governance" / "handoffs" / ".gitkeep", "")
            add_file(root / "artifacts" / "governance" / "reviews" / ".gitkeep", "")

    # ------------------------------------------------------------------
    # Deduplicate directories (preserve declaration order)
    # ------------------------------------------------------------------
    seen_d: set[Path] = set()
    unique_dirs = [d for d in dirs if d not in seen_d and not seen_d.add(d)]  # type: ignore[func-returns-value]

    return ScaffoldPlan(
        root=root,
        profile=init_profile.value,
        template=template,
        scaffold_version=SCAFFOLD_VERSION,
        directories=unique_dirs,
        files=sfiles,
    )


def execute_plan(
    plan: ScaffoldPlan,
    conflict: ConflictPolicy = ConflictPolicy.SKIP,
) -> ScaffoldResult:
    """Execute a scaffold plan, applying the conflict policy for existing files.

    Args:
        plan: ScaffoldPlan from plan_scaffold().
        conflict: How to handle files that already exist.
            SKIP (default) — leave existing files unchanged (safe, idempotent).
            FAIL — raise FileExistsError if any planned file already exists.
            OVERWRITE — replace existing files with the planned content.

    Returns:
        ScaffoldResult tracking every directory and file action taken.

    Raises:
        FileExistsError: If conflict=FAIL and any planned file already exists.
    """
    level = "governed" if plan.template in ("governed", "multi-agent") else plan.template
    result = ScaffoldResult(
        root=plan.root,
        level=level,
        profile=plan.profile,
        template=plan.template,
    )

    for d in plan.directories:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            result.created_dirs.append(d)

    for sf in plan.files:
        if sf.path.exists():
            if conflict == ConflictPolicy.FAIL:
                raise FileExistsError(
                    f"File already exists: {sf.path.relative_to(plan.root)}"
                )
            if conflict == ConflictPolicy.OVERWRITE:
                sf.path.parent.mkdir(parents=True, exist_ok=True)
                sf.path.write_text(sf.content, encoding="utf-8")
                result.overwritten_files.append(sf.path)
            else:
                result.skipped_files.append(sf.path)
        else:
            sf.path.parent.mkdir(parents=True, exist_ok=True)
            sf.path.write_text(sf.content, encoding="utf-8")
            result.created_files.append(sf.path)

    return result


def validate_scaffold(root: Path, plan: ScaffoldPlan) -> list[Issue]:
    """Verify that a scaffold plan was applied successfully.

    Checks that all planned directories and files exist on disk. Suitable for
    post-init integrity verification immediately after execute_plan().

    Args:
        root: Repo root directory (used for readable relative paths in messages).
        plan: ScaffoldPlan that was applied.

    Returns:
        List of Issue objects for missing items. Empty list means the scaffold
        is intact.
    """
    issues: list[Issue] = []

    for d in plan.directories:
        if not d.exists():
            issues.append(
                Issue(
                    code="SCAFFOLD_DIR_MISSING",
                    severity=Severity.ERROR,
                    message=f"Expected directory was not created: {d.relative_to(root)}",
                    path=d,
                )
            )

    for sf in plan.files:
        if not sf.path.exists():
            issues.append(
                Issue(
                    code="SCAFFOLD_FILE_MISSING",
                    severity=Severity.ERROR,
                    message=f"Expected file was not created: {sf.path.relative_to(root)}",
                    path=sf.path,
                )
            )

    return issues


def format_plan(plan: ScaffoldPlan, check_existing: bool = False) -> str:
    """Return a human-readable dry-run preview of a ScaffoldPlan.

    Args:
        plan: The scaffold plan to display.
        check_existing: If True, check the filesystem and annotate items that
            already exist (they would be skipped under the default conflict
            policy).

    Returns:
        Multi-line string suitable for printing to a terminal.
    """
    lines = [
        "DRY RUN — governance-os scaffold plan",
        f"  profile={plan.profile}  template={plan.template}"
        f"  scaffold_version={plan.scaffold_version}",
        f"  root={plan.root}",
    ]

    if plan.directories:
        lines.append(f"\nDirectories ({len(plan.directories)}):")
        for d in plan.directories:
            lines.append(f"  + {d.relative_to(plan.root)}/")

    if plan.files:
        lines.append(f"\nFiles ({len(plan.files)}):")
        for sf in plan.files:
            rel = sf.path.relative_to(plan.root)
            if check_existing and sf.path.exists():
                lines.append(f"  ~ {rel}  (exists — would skip)")
            else:
                lines.append(f"  + {rel}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public convenience entry point
# ---------------------------------------------------------------------------


def init_repo(
    root: Path,
    level: str = "standard",
    profile: str = "generic",
    with_doctrine: bool = False,
    template: str | None = None,
    conflict: ConflictPolicy = ConflictPolicy.SKIP,
) -> ScaffoldResult:
    """Initialize a governance-os repo at *root*.

    Convenience wrapper around plan_scaffold() + execute_plan(). Use those
    functions directly if you need dry-run capability or fine-grained conflict
    control.

    Args:
        root: Target directory (created if it does not exist).
        level: Governance maturity level — "minimal", "standard", or "governed".
            Legacy parameter; prefer *template* for new callers.
        profile: Governance profile — "generic" (default) or "codex".
        with_doctrine: If True, scaffold an optional doctrine file even at
            standard level.
        template: Template name. Takes precedence over *level* when provided.
            Supported values: "minimal", "governed", "multi-agent".
        conflict: How to handle existing files. Default: SKIP (safe, idempotent).

    Returns:
        ScaffoldResult describing every directory and file action taken.

    Raises:
        ValueError: If *template* is given but invalid, if the profile is
            unrecognized, or if the combination is unsupported.
        FileExistsError: If conflict=FAIL and a planned file already exists.
    """
    if template is not None:
        effective_template = template
    else:
        # Legacy --level support: resolve to nearest template equivalent.
        # Invalid levels fall back to "standard" for backward compatibility.
        try:
            init_level = InitLevel(level)
        except ValueError:
            init_level = InitLevel.STANDARD
        effective_template = init_level.value

    plan = plan_scaffold(
        root, profile=profile, template=effective_template, with_doctrine=with_doctrine
    )
    return execute_plan(plan, conflict=conflict)


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

    if result.overwritten_files:
        lines.append("\nFiles overwritten:")
        for f in result.overwritten_files:
            lines.append(f"  ! {f.relative_to(result.root)}")

    if result.skipped_files:
        lines.append("\nFiles skipped (already exist):")
        for f in result.skipped_files:
            lines.append(f"  ~ {f.relative_to(result.root)}")

    return "\n".join(lines)
