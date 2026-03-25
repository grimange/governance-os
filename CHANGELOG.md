# Changelog

All notable changes to governance-os are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [0.2.0] — 2026-03-25

### Added

- `govos preflight` — single fail-closed governance readiness gate composing contract parsing, schema validation, integrity, dependency graph, portability, and optional authority checks
- `govos registry build` — builds a structured registry snapshot from all discovered pipeline contracts; detects duplicate ids, missing stages, empty output declarations
- `govos registry verify` — verifies registry integrity; with `--snapshot` reconciles against a persisted JSON file to detect stale or untracked entries
- `govos audit readiness` — surfaces contracts missing purpose, scope, implementation notes, or adequate success criteria
- `govos audit coverage` — finds pipeline-like directories (Makefile, Dockerfile, build scripts, etc.) without governance contracts
- `govos audit drift` — detects declared output artifacts that do not exist on disk
- `govos discover candidates` — suggests uncontracted pipeline-like directories with confidence levels and suggested ids
- `govos authority verify` — validates that required authority files exist, contracts are not inside generated directories, and dependencies reference ids not paths
- `govos skills index` — indexes skill definitions found under `governance/skills/` or `skills/`
- `govos skills verify` — indexes skills and validates for empty files and duplicate ids
- `govos doctrine validate` — checks that a governance doctrine file is present and non-empty
- `govos init --level` — three governance maturity levels: `minimal`, `standard` (default), `governed`
- `govos init --profile` — optional profiles: `generic` (default) and `codex` (scaffolds session template)
- `govos init --with-doctrine` — scaffolds an optional doctrine file at any level
- `--out <path>` flag on all output commands to write reports to disk
- New result models: `RegistryResult`, `AuditResult`, `AuthorityResult`, `CandidateResult`, `SkillsResult`, `PreflightResult`
- New stable issue codes: `REGISTRY_DUPLICATE_ID`, `REGISTRY_STALE_ENTRY`, `REGISTRY_UNTRACKED_PIPELINE`, `AUTHORITY_MISSING_ROOT`, `AUTHORITY_CONTRACT_IN_ARTIFACT_DIR`, `AUTHORITY_PATH_DEPENDENCY`, `AUDIT_UNCONTRACTED_SURFACE`, `AUDIT_MISSING_OUTPUT`, `AUDIT_NO_PIPELINES`, `SKILLS_DUPLICATE_ID`, `SKILLS_DIR_NOT_FOUND`
- New scaffold templates: `governance-governed.yaml`, `README.governance.governed.md`, `codex-session.md`, `doctrine-template.md`
- 56 new tests (215 total) covering all new commands, modules, and edge cases
- Public API extended: `registry_build()`, `registry_verify()`, `preflight()`, `audit()`, `candidates()`, `authority_verify()`, `skills_index()`, `skills_verify()`

### Changed

- `govos init` now accepts `--level`, `--profile`, and `--with-doctrine` options; existing default behaviour is preserved (`--level standard --profile generic`)
- `format_result()` output now includes `level=` and `profile=` in the summary line
- `pyproject.toml` `B008` added to ruff ignore list (standard Typer usage pattern)

---

## [0.1.0] — 2026-03-25

### Added

- `govos init` — initialises a repo with the standard governance directory layout
- `govos scan` — discovers and parses pipeline contracts from markdown files
- `govos verify` — validates contracts against schema rules and analyses the dependency graph
- `govos status` — classifies each pipeline as `ready`, `blocked`, `invalid`, or `orphaned`
- `govos portability scan` — detects non-portable output path declarations
- All commands support `--json` for machine-readable output
- Pydantic-typed result models (`ScanResult`, `VerifyResult`, `StatusResult`, `PortabilityResult`)
- Stable issue codes for structured diagnostics (`MISSING_REQUIRED_FIELD`, `UNRESOLVED_DEPENDENCY`, `DEPENDENCY_CYCLE`, `ABSOLUTE_PATH`, etc.)
- Python public API (`governance_os.api`) mirroring the CLI surface
- `governance.yaml` configuration with `pipelines_dir` and `contracts_glob` fields
- Embedded scaffold templates for `governance.yaml` and `README.governance.md`
- 149-test suite covering CLI, parsing, validation, graph analysis, and reporting
