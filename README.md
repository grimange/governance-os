# governance-os

A universal Python governance runtime for pipeline contract management.

Install once. Use in any repo. No template duplication required.

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
# 1. Initialise a repo
govos init

# 2. Discover pipeline contracts
govos scan

# 3. Validate contracts and dependency graph
govos verify

# 4. Report pipeline readiness
govos status

# 5. Check for portability issues
govos portability scan
```

All commands accept a path argument (defaults to `.`) and a `--json` flag for machine-readable output.

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
Bootstrap the project structure.

Depends on:
- none

Inputs:
- pyproject.toml template

Outputs:
- src/mypackage/__init__.py
- pyproject.toml

Implementation Notes:
Use a src/ layout.

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

### `govos init [PATH]`

Initialises a governance-os repo at PATH (default `.`).

Creates:
- `governance/pipelines/` — pipeline contracts directory
- `docs/governance/` — governance documentation
- `artifacts/` — build and verification artifacts
- `governance.yaml` — default configuration
- `governance/pipelines/001--example.md` — starter pipeline
- `docs/governance/README.governance.md` — governance overview

Safe to run multiple times. Existing files are never overwritten.

### `govos scan [PATH] [--json]`

Discovers and parses pipeline contracts. Reports parse errors including filename violations.

### `govos verify [PATH] [--json]`

Validates all contracts against schema rules, checks naming integrity, and analyses the dependency graph. Exits 0 on pass, 1 on failure.

### `govos status [PATH] [--json]`

Classifies each pipeline as `ready`, `blocked`, `invalid`, or `orphaned`.

### `govos portability scan [PATH] [--json]`

Scans output declarations for non-portable paths (absolute paths, Windows drive letters, path traversal). Exits 0 on pass, 1 on failure.

---

## Python API

```python
from pathlib import Path
import governance_os.api as api

root = Path(".")

scan_result     = api.scan(root)        # ScanResult
verify_result   = api.verify(root)      # VerifyResult
status_result   = api.status(root)      # StatusResult
port_result     = api.portability(root) # PortabilityResult
```

All functions return typed Pydantic models. See `src/governance_os/models/` for the full model definitions.

---

## Development

```
pip install -e ".[dev]"
pytest
```

---

## Version

`0.1.0`
