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

After running `govos init`, your repo will contain:

```
your-repo/
├── governance/
│   └── pipelines/
│       └── 001--example.md     # pipeline contracts
├── docs/
│   └── governance/
│       └── README.governance.md
├── artifacts/                  # build and verification outputs
└── governance.yaml             # govos configuration
```

For `govos init --level governed`:

```
your-repo/
├── governance/
│   ├── pipelines/
│   ├── skills/                 # optional skill references
│   └── doctrine/               # optional governance doctrine
├── docs/governance/
├── artifacts/governance/       # registry snapshots and audit reports
└── governance.yaml
```

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

### `govos init [PATH] [--level LEVEL] [--profile PROFILE] [--with-doctrine]`

Initialises a governance-os repo at PATH (default `.`).

**Levels:**

| Level | Creates |
|---|---|
| `minimal` | `governance/pipelines/`, `artifacts/`, `governance.yaml` |
| `standard` | above + `docs/governance/` (default) |
| `governed` | above + `artifacts/governance/`, `governance/skills/`, `governance/doctrine/` |

**Profiles:**

| Profile | Extra assets |
|---|---|
| `generic` | none (default) |
| `codex` | `governance/sessions/session-template.md` |

`--with-doctrine` scaffolds a doctrine file at the standard level.

Safe to run multiple times — existing files are never overwritten.

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

| Profile | Default plugins | Expected surfaces |
|---|---|---|
| `generic` | none | `governance/pipelines`, `artifacts`, `governance.yaml` |
| `codex` | `codex_instructions` | above + `AGENTS.md` |

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

### Plugin activation (deterministic)

```
active = profile.default_plugins
       + config.enabled_plugins     (deduplicated, config order)
       - config.disabled_plugins
```

Only plugins in the built-in registry can be activated. Unknown plugin IDs are silently ignored.

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
govos init --profile generic    # default, no agent-specific assets
govos init --profile codex      # creates AGENTS.md + governance/sessions/
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
```

All functions return typed Pydantic models. See `src/governance_os/models/` for full model definitions.

---

## Issue Codes

All diagnostics use stable, machine-readable codes:

| Code | Severity | Description |
|---|---|---|
| `MISSING_PIPELINES_DIR` | error | Pipelines directory not found |
| `FILENAME_PARSE_ERROR` | error | Filename doesn't match `<id>--<slug>.md` |
| `MISSING_REQUIRED_FIELD` | error | Required contract field is missing |
| `INVALID_STAGE` | error | Stage not in allowed set |
| `DUPLICATE_PIPELINE_ID` | error | Multiple pipelines share the same numeric id |
| `UNRESOLVED_DEPENDENCY` | error | Depends on a non-existent pipeline |
| `DEPENDENCY_CYCLE` | error | Circular dependency detected |
| `ABSOLUTE_PATH` | error | Output path is absolute (not portable) |
| `WINDOWS_DRIVE_PATH` | error | Output path contains Windows drive letter |
| `PATH_TRAVERSAL` | error | Output path contains `../` traversal |
| `HOME_RELATIVE_PATH` | error | Output path starts with `~` |
| `REGISTRY_DUPLICATE_ID` | error | Registry has duplicate pipeline id |
| `AUTHORITY_MISSING_ROOT` | error | Required authority file is missing |
| `AUTHORITY_CONTRACT_IN_ARTIFACT_DIR` | error | Contract file inside generated directory |
| `AUDIT_UNCONTRACTED_SURFACE` | warning | Pipeline-like directory without a contract |
| `AUDIT_MISSING_OUTPUT` | warning | Declared output artifact does not exist |
| `REGISTRY_STALE_ENTRY` | warning | Registry snapshot has entry no longer discovered |
| `REGISTRY_UNTRACKED_PIPELINE` | warning | Discovered pipeline absent from registry snapshot |

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
