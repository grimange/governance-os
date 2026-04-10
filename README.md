# governance-os

A lightweight governance runtime for pipeline contract management.

Define structured pipeline contracts in plain markdown. governance-os discovers, validates, and reports on them — in any repository, with zero configuration required.

---

## What it does

governance-os treats your build, release, or implementation pipeline as a set of **contracts**: markdown files that describe what each pipeline stage does, what it depends on, and what artifacts it produces.

The runtime provides:

- **Discovery** — finds all pipeline contracts under a configured directory
- **Validation** — checks required fields, allowed stage values, and naming integrity
- **Dependency analysis** — builds a dependency graph, detects unresolved references and cycles
- **Readiness classification** — reports each pipeline as `ready`, `blocked`, `invalid`, or `orphaned`
- **Portability checks** — scans output declarations for non-portable paths
- **Pipeline registry** — builds and verifies a structured snapshot of the governed pipeline set
- **Preflight check** — single fail-closed governance readiness gate, profile-aware
- **Audit analysis** — deeper governance coverage checks (readiness, coverage, drift)
- **Authority validation** — verifies source-of-truth configuration
- **Candidate discovery** — finds uncontracted pipeline-like directories
- **Skills index** — indexes and validates reusable skill references
- **Init profiles and levels** — scaffold governance at different maturity levels
- **Governance scoring** — explainable score across five categories with prioritized findings, cross-signal insights, and optional trend comparison (v0.4)
- **Profile + plugin system** — lightweight, statically registered internal plugins driven by repo profile (v0.5)
- **Pipeline lifecycle state machine** — infers effective pipeline state (draft, ready, active, blocked, completed, failed, archived) from marker files, contracts, and the dependency graph (v0.8)

---

## Install

```
pip install governance-os
```

Or in editable mode for development:

```
pip install -e ".[dev]"
```

**Requires Python 3.11+**

---

## Quick Start

```
# 1. Initialise a repo with the default structure
govos init

# 2. Run a preflight governance check (fail-closed)
govos preflight

# 3. Discover and parse pipeline contracts
govos scan

# 4. Validate contracts and the dependency graph
govos verify

# 5. Report pipeline readiness
govos status

# 6. Check output declarations for portability issues
govos portability scan
```

All commands accept a `PATH` argument (defaults to `.`) and a `--json` flag for machine-readable output.
Most commands also accept `--out <path>` to write a report file to disk.

---

## Repository Layout

`govos init` supports two dimensions: **profile** (environment conventions) and **template** (scaffold surface area).

### Profiles

| Profile | Description |
|---|---|
| `generic` | Vendor-neutral. No agent-specific assumptions. Default. |
| `codex` | Adds `AGENTS.md`, `.codex/config.toml`, and session contracts. |

### Templates

| Template | Surface area |
|---|---|
| `minimal` | `governance/pipelines/`, `artifacts/`, `governance.yaml` |
| `governed` | above + `docs/governance/`, `governance/skills/`, `governance/doctrine/`, `artifacts/governance/` |
| `multi-agent` | `governed` + role definitions, role contracts, workflow contract, handoff/review dirs (codex only) |

### Scaffold combinations

**`generic:minimal`** — bare governance structure:

```
your-repo/
├── governance/pipelines/001--example.md
├── artifacts/
└── governance.yaml             # includes profile: generic
```

**`codex:minimal`** — minimal with Codex instruction surfaces:

```
your-repo/
├── governance/
│   ├── pipelines/001--example.md
│   └── sessions/session-template.md
├── artifacts/
├── AGENTS.md                   # short operational instructions
├── .codex/config.toml          # Codex profile config
└── governance.yaml             # includes profile: codex
```

**`codex:governed`** — full governance with layered Codex assets:

```
your-repo/
├── governance/
│   ├── pipelines/
│   ├── sessions/
│   ├── skills/govos-preflight.skill.md
│   └── doctrine/doctrine.md
├── docs/governance/
├── artifacts/governance/
├── AGENTS.md
├── .codex/config.toml
└── governance.yaml
```

**`codex:multi-agent`** — multi-agent role structure (extends governed):

```
your-repo/
├── .codex/
│   ├── config.toml
│   └── agents/
│       ├── planner.toml        # role definition
│       ├── implementer.toml
│       └── reviewer.toml
├── docs/
│   ├── governance/agents/
│   │   ├── planner.md          # role governance contract
│   │   ├── implementer.md
│   │   └── reviewer.md
│   └── contracts/
│       └── multi-agent-workflow.md
├── artifacts/governance/
│   ├── handoffs/               # planner deposits handoff records here
│   └── reviews/                # implementer/reviewer exchange here
├── governance/  (all governed assets)
├── AGENTS.md
└── governance.yaml             # includes enabled_plugins: [multi_agent]
```

`AGENTS.md` is kept short and operational. Role procedures live in `docs/governance/agents/` and the workflow contract lives in `docs/contracts/` — neither burdens the always-read instruction surface.

---

## Pipeline Contract Format

Pipeline contracts are plain markdown files stored under `governance/pipelines/`.

### Filename Convention

```
<numeric-id>--<slug>.md
```

Examples:
- `001--establish-skeleton.md`
- `042--verify-outputs.md`

The numeric id must be unique across the repo. The slug must be lowercase alphanumeric with hyphens.

### Contract Structure

```markdown
# 001 — Establish Skeleton

Stage: establish

Purpose:
Bootstrap the project structure with the minimum viable src layout.

Depends on:
- none

Inputs:
- pyproject.toml template

Outputs:
- src/mypackage/__init__.py
- pyproject.toml

Implementation Notes:
Use a src/ layout. CLI entry point must resolve after editable install.

Success Criteria:
- Package installs in editable mode
- CLI entry point resolves

Out of Scope:
- Real command behaviour
```

### Allowed Stage Values

| Stage | Meaning |
|---|---|
| `establish` | Foundation and setup work |
| `implement` | Feature implementation |
| `verify` | Testing and validation |
| `report` | Reporting and documentation |
| `release` | Release preparation |

### Dependency References

`Depends on:` lists numeric ids of prerequisite pipelines:

```markdown
Depends on:
- 001
- 003
```

Use `none` when there are no dependencies:

```markdown
Depends on:
- none
```

---

## Configuration

`governance.yaml` in the repo root controls discovery behaviour.

```yaml
# governance-os configuration
pipelines_dir: governance/pipelines
contracts_glob: "**/*.md"
```

| Field | Default | Description |
|---|---|---|
| `pipelines_dir` | `pipelines` | Directory containing pipeline contracts (relative to repo root) |
| `contracts_glob` | `**/*.md` | Glob pattern used to find contract files |

The package runs with defaults if `governance.yaml` is absent.

---

## CLI Reference

All commands listed here are stable as of v0.9.0. The `govos-mcp` server entry point is available but documented separately — it is not a `govos` subcommand.

### `govos init [PATH] [--profile PROFILE] [--template TEMPLATE] [--with-doctrine] [--dry-run] [--force]`

Initialises a governance-os repo at PATH (default `.`).

```
govos init --profile generic --template minimal        # bare structure
govos init --profile codex --template minimal          # Codex with minimal scaffold
govos init --profile codex --template governed         # Codex with full governance surface
govos init --profile codex --template multi-agent      # Codex with role-specialized agents
govos init --dry-run                                   # preview without writing files
govos init --force                                     # overwrite existing files
```

**`--profile`:** `generic` (default) or `codex`

**`--template`:** `minimal`, `governed`, or `multi-agent` (codex only)

**`--dry-run`:** Print the full scaffold plan (directories and files) without writing anything to disk. Output is identical to what would be executed, making it safe to inspect before committing.

**`--force`:** Overwrite existing files with planned content instead of skipping them (default behaviour is skip — safe for re-running on an existing repo).

| Template | Creates |
|---|---|
| `minimal` | `governance/pipelines/`, `artifacts/`, `governance.yaml` |
| `governed` | above + `docs/governance/`, `governance/skills/`, `governance/doctrine/`, `artifacts/governance/` |
| `multi-agent` | `governed` + `.codex/agents/` role definitions, `docs/governance/agents/` contracts, `docs/contracts/multi-agent-workflow.md`, `artifacts/governance/handoffs/`, `artifacts/governance/reviews/` |

The `codex` profile adds `AGENTS.md`, `.codex/config.toml`, and `governance/sessions/` on top of the selected template. The `multi-agent` template also adds `enabled_plugins: [multi_agent]` to `governance.yaml`.

`--with-doctrine` scaffolds a doctrine file without requiring the full `governed` template.

`--level` is a legacy alias for `--template` and still works (`minimal`, `standard`, `governed`).

Generated `governance.yaml` includes the active `profile:` field. Existing files are never overwritten.

---

### `govos scan [PATH] [--json] [--out PATH]`

Discovers and parses pipeline contracts. Reports parse errors including filename violations.

### `govos verify [PATH] [--json] [--out PATH]`

Validates all contracts against schema rules, checks naming integrity, and analyses the dependency graph. Exits `0` on pass, `1` on failure.

### `govos status [PATH] [--json] [--out PATH]`

Classifies each pipeline as `ready`, `blocked`, `invalid`, or `orphaned`.

### `govos preflight [PATH] [--json] [--out PATH] [--authority] [--no-portability]`

Runs a single fail-closed governance readiness check that composes:
- contract parsing
- schema and integrity validation
- dependency graph analysis
- portability checks (disable with `--no-portability`)
- authority validation (enable with `--authority`)

Exits `0` on pass, `1` on any error.

### `govos portability scan [PATH] [--json] [--out PATH]`

Scans output declarations for non-portable paths (absolute paths, Windows drive letters, home-directory `~`, path traversal `..`). Exits `0` on pass, `1` on failure.

---

### `govos registry build [PATH] [--json] [--out PATH]`

Builds a registry snapshot from all discovered pipeline contracts. Detects duplicate ids, missing stages, and empty output declarations.

### `govos registry verify [PATH] [--json] [--out PATH] [--snapshot PATH]`

Verifies registry integrity. With `--snapshot`, reconciles against an existing JSON registry file to detect stale or untracked entries.

---

### `govos audit readiness [PATH] [--json] [--out PATH]`

Audits governance readiness: finds contracts missing purpose, scope, implementation notes, or adequate success criteria.

### `govos audit coverage [PATH] [--json] [--out PATH]`

Audits governance coverage: finds pipeline-like directories (containing Makefile, Dockerfile, build scripts, etc.) that have no governance contract.

### `govos audit drift [PATH] [--json] [--out PATH]`

Audits output drift: finds declared output artifacts that do not exist on disk.

### `govos audit multi-agent [PATH] [--json] [--out PATH]`

Audits multi-agent Codex setup for structural completeness. Checks:
- `.codex/agents/` role definitions (planner, implementer, reviewer)
- `docs/governance/agents/` role governance contracts
- `docs/contracts/multi-agent-workflow.md` workflow contract
- `artifacts/governance/handoffs/` and `artifacts/governance/reviews/` artifact directories

Missing reviewer role is an ERROR (role collapse risk). Other missing roles and contracts are WARNINGs. Missing artifact directories are INFO.

Activate the `multi_agent` plugin in `governance.yaml` to run these checks automatically as part of `govos preflight`:

```yaml
enabled_plugins:
  - multi_agent
```

This is set automatically when using `govos init --profile codex --template multi-agent`.

---

### `govos discover candidates [PATH] [--json] [--out PATH]`

Discovers pipeline-like directories lacking governance contracts. Returns candidates with suggested ids, confidence levels, and reasons.

---

### `govos authority verify [PATH] [--json] [--out PATH]`

Validates authority and source-of-truth configuration:
- Required authority files exist (`governance.yaml`)
- No pipeline contracts are inside artifact/generated directories
- Dependency references use numeric ids, not file paths
- Configured directories exist

Exits `0` on pass, `1` on error.

---

### `govos skills index [PATH] [--json] [--out PATH]`

Indexes all skill definitions found in `governance/skills/` (or `skills/`). Reports skill ids, names, and descriptions.

### `govos skills verify [PATH] [--json] [--out PATH]`

Indexes skills and validates them: detects empty files and duplicate ids.

---

### `govos doctrine validate [PATH]`

Validates that a governance doctrine file exists at `governance/doctrine/doctrine.md` and is non-empty.

---

### `govos score [PATH] [--json] [--out PATH] [--compare PATH] [--explain]`

Computes an explainable governance score by running all checks and combining their findings.

**Categories scored:**

| Category | Source checks |
|---|---|
| `integrity` | parse errors, schema validation, integrity, dependency graph, portability |
| `readiness` | audit readiness (purpose, scope, success criteria, implementation notes) |
| `coverage` | audit coverage (uncontracted pipeline surfaces) |
| `drift` | audit drift (missing declared output artifacts) |
| `authority` | authority validation issues |

**Scoring formula:**

Each category starts at 100. Deductions are applied per finding:
- Error: -25 points each
- Warning: -10 points each
- Info findings: not scored

Score floors at 0. Overall score is the mean of all category scores (rounded).

**Grade bands:**

| Score | Grade |
|---|---|
| 90–100 | A |
| 75–89 | B |
| 60–74 | C |
| 40–59 | D |
| 0–39 | F |

**Options:**

- `--compare PATH` — provide a path to a previous `govos score --json` output to see a delta summary
- `--explain` — include the formula explanation in the output

**Sample console output:**

```
Score: 72/100  Grade: C
  integrity: 50/100  (2 errors × 25 = -50 pts)
  readiness: 80/100  (2 warnings × 10 = -20 pts)
  coverage: 90/100  (1 warning × 10 = -10 pts)
  drift: 100/100
  authority: 40/100  (1 error × 25 = -25 pts; 3 warnings × 10 = -30 pts)

2 derived insight(s):
  [HIGH] Contract quality gap: multiple documentation deficiencies in same pipeline(s)
    Pipeline(s) ['001'] each have 2 or more documentation quality issues. ...
  [MEDIUM] Contract candidates available for uncontracted surfaces
    Coverage gaps (AUDIT_UNCONTRACTED_SURFACE) were found alongside 2 candidate(s). ...

Findings: 4 high, 6 medium, 2 low
  [HIGH] [MISSING_REQUIRED_FIELD] Pipeline '001' is missing required field: title.
  ...
```

**Derived insights** are cross-signal conclusions drawn from combining multiple findings:

| Code | Trigger | Priority |
|---|---|---|
| `INSIGHT_CANDIDATE_READY` | `AUDIT_UNCONTRACTED_SURFACE` + candidates discovered | medium |
| `INSIGHT_PIPELINE_INCONSISTENCY` | `AUDIT_MISSING_OUTPUT` + `REGISTRY_STALE_ENTRY` on same pipeline | high |
| `INSIGHT_GOVERNANCE_BREAKDOWN` | `AUTHORITY_MISSING_ROOT` + `MISSING_REQUIRED_FIELD` | high |
| `INSIGHT_CONTRACT_QUALITY_GAP` | 2+ documentation issues on same pipeline | medium |
| `INSIGHT_GRAPH_INTEGRITY_FAILURE` | `DEPENDENCY_CYCLE` + `UNRESOLVED_DEPENDENCY` | high |

**Limitations:**

- The score is not a certification or compliance indicator. It is a structured summary of current findings.
- Scores are reproducible given the same repository state. They do not drift between runs unless findings change.
- Category weights are equal (simple mean). No hidden weighting.
- Delta comparison requires a previous score report saved with `--json --out`. Non-score JSON files are rejected.
- Insights are pattern-matched, not inferred. They can only trigger on known code combinations.

---

## Profiles and Plugins (v0.5)

### What profiles are

Profiles define repo-level governance conventions. They set:
- expected surfaces (files/directories that should exist)
- default active plugins
- scaffold asset groups applied by `govos init`

Profiles are **data definitions**, not code. They do not change the core runtime behavior — they select which optional plugins run.

### Available profiles

| Profile | Templates | Default plugins | Expected surfaces |
|---|---|---|---|
| `generic` | `minimal`, `governed` | none | `governance/pipelines`, `artifacts`, `governance.yaml` |
| `codex` | `minimal`, `governed` | `codex_instructions` | above + `AGENTS.md` |

### What plugins are

Plugins add optional validation checks on top of the core runtime. They are:
- first-party (no external loading)
- statically registered (inspectable at any time)
- additive (they do not replace core checks)

| Plugin ID | What it checks |
|---|---|
| `authority` | source-of-truth configuration (governance.yaml, contract locations) |
| `doctrine` | governance doctrine files in `governance/doctrine/` |
| `skills` | skill definitions in `governance/skills/` |
| `codex_instructions` | `AGENTS.md` existence and content |
| `multi_agent` | multi-agent Codex structure (role definitions, role contracts, workflow contract, artifact dirs) |

### Plugin activation (deterministic)

```
active = profile.default_plugins
       + config.enabled_plugins     (deduplicated, config order)
       - config.disabled_plugins
```

Only plugins in the built-in registry can be activated. Unknown plugin IDs in
`enabled_plugins` or `disabled_plugins` emit a `PLUGIN_UNKNOWN` warning during `govos preflight`.

### Configuring the profile in governance.yaml

```yaml
profile: codex

# Optional overrides:
enabled_plugins:
  - doctrine
  - skills
disabled_plugins:
  - codex_instructions
```

### Difference between generic and codex

- `generic` — vendor-neutral, no agent-specific assumptions, no extra plugins
- `codex` — Codex-oriented; activates `codex_instructions` (checks for `AGENTS.md`), scaffolds session contracts and `AGENTS.md`

The core runtime remains the same for both. Profile selection is purely additive.

### Profile-aware init

```
govos init --profile generic --template minimal    # bare governance structure
govos init --profile codex --template minimal      # Codex: AGENTS.md + .codex/config.toml + sessions
govos init --profile codex --template governed     # above + skills + doctrine + registry artifacts
```

### Profile-aware validation

Preflight automatically activates plugins based on the configured profile:

```
# In a codex-profile repo (profile: codex in governance.yaml):
govos preflight
# — runs all core checks
# — also runs codex_instructions plugin (checks AGENTS.md)
# — findings include source="codex_instructions" on plugin-generated issues
```

### Limitations

- Only `generic` and `codex` profiles are built-in. There is no third-party profile registry.
- Plugins are internal and cannot be loaded from user code.
- Profile does not change the schema validation rules — contract format is universal.
- `govos verify` is not profile-aware; it validates contracts only. Profile checks are in `govos preflight`.

---

### `govos profile list`

Lists all available governance profiles with their default plugins.

### `govos profile show PROFILE_ID`

Shows full details of a specific profile, including expected surfaces and optional surfaces.

### `govos profile validate [PATH] [--json] [--out PATH]`

Checks whether the repo satisfies the expected surfaces for its configured profile.
Reads `profile` from `governance.yaml` (defaults to `generic`).
Exits `0` if all expected surfaces exist, `1` if any are missing.

---

### `govos pipeline list [PATH] [--json]`

Lists all pipelines with their effective lifecycle states. Infers state from marker files, contract declarations, schema validity, and dependency graph.

**Lifecycle states:**

| State | Meaning |
|---|---|
| `draft` | Contract has schema errors; required sections missing or invalid |
| `ready` | All dependencies resolved; no blockers |
| `active` | Run directory present at `artifacts/governance/runs/<id>/` |
| `blocked` | A dependency is in a blocking state, or an external block marker exists |
| `completed` | Declared completed in contract |
| `failed` | Failure marker present at `artifacts/governance/failures/<id>.md` |
| `archived` | Declared archived in contract |

### `govos pipeline status PIPELINE_ID [--root PATH] [--json]`

Shows the lifecycle status for a single pipeline. `PIPELINE_ID` is the numeric id (e.g. `001`) or slug.

### `govos pipeline verify PIPELINE_ID [--root PATH]`

Verifies lifecycle integrity for a single pipeline. Exits `1` if there is lifecycle drift (declared state in contract does not match the inferred effective state).

---

### `govos plugin list`

Lists all registered governance plugins with their IDs and descriptions. Always exits `0`.

### `govos plugin show PLUGIN_ID`

Shows details of a specific plugin. Exits `0` if found, `2` if not found.

**Available plugin IDs:** `authority`, `doctrine`, `skills`, `codex_instructions`, `multi_agent`

---

## Python API

```python
from pathlib import Path
import governance_os.api as api

root = Path(".")

# Core commands
scan_result      = api.scan(root)             # ScanResult
verify_result    = api.verify(root)           # VerifyResult
status_result    = api.status(root)           # StatusResult
port_result      = api.portability(root)      # PortabilityResult

# Phase 1 — Operational
preflight_result = api.preflight(root)        # PreflightResult
registry_result  = api.registry_build(root)  # RegistryResult
reg_verify       = api.registry_verify(root) # RegistryResult

# Phase 2 — Analysis
audit_ready      = api.audit(root, mode="readiness")  # AuditResult
audit_cov        = api.audit(root, mode="coverage")   # AuditResult
audit_drift      = api.audit(root, mode="drift")      # AuditResult
candidates       = api.candidates(root)               # CandidateResult
authority        = api.authority_verify(root)         # AuthorityResult

# Phase 3 — Optional
skills           = api.skills_index(root)    # SkillsResult
skills_v         = api.skills_verify(root)   # SkillsResult

# v0.4 — Intelligence
score_result     = api.score(root)                          # ScoreResult
score_with_delta = api.score(root, compare_path=Path("prev.json"))  # ScoreResult with delta

# v0.5 — Profiles and plugins
profiles         = api.profile_list()                       # list[ProfileDefinition]
profile          = api.profile_show("codex")                # ProfileDefinition | None
profile, missing = api.profile_validate(root)               # (ProfileDefinition, list[str])
plugins          = api.plugin_list()                        # list[Plugin]
plugin           = api.plugin_show("authority")             # Plugin | None

# v0.8 — Pipeline lifecycle
lifecycle        = api.pipeline_lifecycle(root)             # LifecycleResult
record           = api.pipeline_lifecycle_status(root, "001")  # LifecycleRecord | None
```

All functions return typed Pydantic models. See `src/governance_os/models/` for full model definitions.

---

## Issue Codes

All diagnostics use stable, machine-readable codes. Severity levels: **error** (causes exit 1), **warning** (logged, does not block pass), **info** (informational only).

### Parse and contract validation

| Code | Severity | Description |
|---|---|---|
| `MISSING_PIPELINES_DIR` | error | Pipelines directory not found |
| `FILENAME_PARSE_ERROR` | error | Filename doesn't match `<id>--<slug>.md` |
| `MISSING_REQUIRED_FIELD` | error | Required contract field is missing |
| `INVALID_STAGE` | error | Stage not in allowed set |
| `EMPTY_LIST_ENTRY` | warning | List field contains an empty entry |
| `DUPLICATE_LIST_ENTRY` | warning | List field contains a duplicate entry |
| `DUPLICATE_PIPELINE_ID` | error | Multiple pipelines share the same numeric id |
| `UNRESOLVED_DEPENDENCY` | error | Depends on a non-existent pipeline |
| `DEPENDENCY_CYCLE` | error | Circular dependency detected |

### Portability

| Code | Severity | Description |
|---|---|---|
| `ABSOLUTE_PATH` | error | Output path is absolute (not portable) |
| `WINDOWS_DRIVE_PATH` | error | Output path contains a Windows drive letter |
| `PATH_TRAVERSAL` | error | Output path contains `../` traversal |
| `HOME_RELATIVE_PATH` | error | Output path starts with `~` |

### Registry

| Code | Severity | Description |
|---|---|---|
| `REGISTRY_DUPLICATE_ID` | error | Registry has duplicate pipeline id |
| `REGISTRY_FILE_INVALID` | error | Registry snapshot file is not valid JSON |
| `REGISTRY_MISSING_STAGE` | warning | Registry entry is missing the stage field |
| `REGISTRY_NO_OUTPUTS` | warning | Registry entry declares no outputs |
| `REGISTRY_FILE_MISSING` | warning | Registry snapshot file does not exist |
| `REGISTRY_STALE_ENTRY` | warning | Registry snapshot has entry no longer discovered |
| `REGISTRY_UNTRACKED_PIPELINE` | warning | Discovered pipeline absent from registry snapshot |

### Authority

| Code | Severity | Description |
|---|---|---|
| `AUTHORITY_MISSING_ROOT` | error | Required authority file (`governance.yaml`) is missing |
| `AUTHORITY_CONTRACT_IN_ARTIFACT_DIR` | error | Contract file is inside a generated/artifact directory |
| `AUTHORITY_CONFIG_INVALID` | error | `governance.yaml` is present but not valid YAML |
| `AUTHORITY_PATH_DEPENDENCY` | warning | Dependency reference uses a file path instead of a numeric id |
| `AUTHORITY_CONFIG_DIR_MISSING` | warning | A directory configured in `governance.yaml` does not exist |

### Audit readiness

| Code | Severity | Description |
|---|---|---|
| `AUDIT_MISSING_PURPOSE` | warning | Contract has no Purpose section |
| `AUDIT_MISSING_SCOPE` | info | Contract has no Scope section |
| `AUDIT_WEAK_SUCCESS_CRITERIA` | info | Contract has only one success criterion |
| `AUDIT_MISSING_IMPL_NOTES` | info | Contract has no Implementation Notes section |
| `AUDIT_NO_PIPELINES` | warning | No pipeline contracts discovered |

### Audit coverage and drift

| Code | Severity | Description |
|---|---|---|
| `AUDIT_UNCONTRACTED_SURFACE` | warning | Pipeline-like directory without a governance contract |
| `AUDIT_NO_SURFACES_FOUND` | info | No pipeline-like directories detected |
| `AUDIT_MISSING_OUTPUT` | warning | Declared output artifact does not exist on disk |
| `AUDIT_NO_DRIFT` | info | No declared output drift detected |

### Multi-agent audit

| Code | Severity | Description |
|---|---|---|
| `MULTIAGENT_MISSING_REVIEWER` | error | Reviewer role definition missing (role collapse risk) |
| `MULTIAGENT_MISSING_WORKFLOW` | warning | `docs/contracts/multi-agent-workflow.md` is missing |
| `MULTIAGENT_SETUP_MISSING` | warning | `.codex/agents/` directory does not exist |
| `MULTIAGENT_MISSING_ROLE_DEF` | warning | A required role definition (`.codex/agents/<role>.toml`) is missing |
| `MULTIAGENT_MISSING_ROLE_CONTRACT` | warning | A role governance contract (`docs/governance/agents/<role>.md`) is missing |
| `MULTIAGENT_EMPTY_ROLE_CONTRACT` | warning | A role governance contract exists but is empty |
| `MULTIAGENT_ROLE_MISMATCH` | warning | Role has a `.toml` definition but no matching governance contract |
| `MULTIAGENT_MISSING_HANDOFFS_DIR` | info | `artifacts/governance/handoffs/` directory not found |
| `MULTIAGENT_MISSING_REVIEWS_DIR` | info | `artifacts/governance/reviews/` directory not found |

### Pipeline lifecycle

| Code | Severity | Description |
|---|---|---|
| `LIFECYCLE_FAILED` | error | Pipeline is in FAILED state (failure marker present) |
| `LIFECYCLE_DRIFT` | warning | Declared state in contract differs from inferred effective state |
| `LIFECYCLE_INVALID_DECLARED_STATE` | warning | `State:` field contains an unrecognised lifecycle value |

### Skills and doctrine

| Code | Severity | Description |
|---|---|---|
| `DOCTRINE_MISSING` | error | Doctrine file not found at `governance/doctrine/doctrine.md` |
| `SKILLS_DUPLICATE_ID` | warning | Two skill files share the same skill id |
| `DOCTRINE_EMPTY` | warning | Doctrine file exists but is empty |
| `DOCTRINE_INCOMPLETE` | warning | Doctrine file exists but is missing expected sections |
| `SKILLS_EMPTY_FILE` | warning | A skill file exists but has no content |
| `SKILLS_DIR_NOT_FOUND` | info | Skills directory (`governance/skills/`) does not exist |

### Codex profile plugin

| Code | Severity | Description |
|---|---|---|
| `CODEX_MISSING_AGENTS_MD` | warning | `AGENTS.md` not found (required for codex profile) |
| `CODEX_EMPTY_AGENTS_MD` | warning | `AGENTS.md` exists but is empty |
| `CODEX_AGENTS_MD_SPARSE` | info | `AGENTS.md` exists but is very short (fewer than 5 lines) |

---

## Development Setup

```
git clone <repo>
cd governance-os
pip install -e ".[dev]"
pytest
```

### Lint and format

```
ruff check src/ tests/
black --check src/ tests/
ruff check --fix src/ tests/
black src/ tests/
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT
