# Changelog

All notable changes to governance-os are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [0.5.0] — 2026-03-26

### Added

- **Profile system** — first-class `ProfileDefinition` model with id, name, description, default plugins, expected surfaces, and scaffold groups
- Built-in profiles: `generic` (no default plugins, vendor-neutral) and `codex` (activates `codex_instructions` plugin, expects `AGENTS.md`)
- `govos profile list` — lists all registered profiles with their default plugins
- `govos profile show <id>` — shows full profile details including expected and optional surfaces
- `govos profile validate [PATH] [--json] [--out]` — checks whether the repo satisfies all expected surfaces for its configured profile; exits `1` if surfaces are missing
- **Internal plugin system** — `Plugin` ABC with `run_checks(root, pipelines) -> list[Issue]`; all plugins are first-party and statically registered
- Built-in plugins: `authority`, `doctrine`, `skills`, `codex_instructions`
- `codex_instructions` plugin — checks for `AGENTS.md` at the repo root; emits `CODEX_MISSING_AGENTS_MD` (warning), `CODEX_EMPTY_AGENTS_MD` (warning), `CODEX_AGENTS_MD_SPARSE` (info)
- Plugin activation model: `profile.default_plugins + config.enabled_plugins − config.disabled_plugins`; unknown plugin IDs are silently ignored
- `GovernanceConfig` extended with `profile` (default `"generic"`), `enabled_plugins` (default `[]`), `disabled_plugins` (default `[]`) — fully backward-compatible
- `Issue.source` optional field — plugin-generated issues carry `source=plugin_id`; core issues leave it `None`
- `govos init --profile codex` now also scaffolds `AGENTS.md` with governance instructions
- 70 new tests covering profile definitions, resolution, surface validation, plugin registry, all four plugins, activation logic, authority deduplication, and profile-aware preflight (378 total)

### Changed

- `api.preflight()` — extended with a plugin step (step 7) that runs active plugins based on the configured profile; additive, no breaking changes; `include_authority=True` suppresses the `authority` plugin to avoid duplication
- JSON issue output now includes a `"source"` key when `Issue.source` is set (omitted when `None` to preserve existing schema for core issues)
- README updated with Profiles and Plugins section documenting architecture, activation rules, configuration, and limitations

---

## [0.4.0] — 2026-03-26

### Added

- `govos score [PATH] [--json] [--out] [--compare] [--explain]` — computes an explainable governance score across five categories: integrity, readiness, coverage, drift, authority
- Scoring formula: per category start=100, error=−25, warning=−10, info=not scored, floor=0; overall = mean of category scores; grade bands A/B/C/D/F
- Prioritized findings: every finding is classified HIGH/MEDIUM/LOW based on explicit code membership with severity fallback; sorted findings included in score output
- Five cross-signal derived insights that fire when specific code combinations are detected: `INSIGHT_CANDIDATE_READY`, `INSIGHT_PIPELINE_INCONSISTENCY`, `INSIGHT_GOVERNANCE_BREAKDOWN`, `INSIGHT_CONTRACT_QUALITY_GAP`, `INSIGHT_GRAPH_INTEGRITY_FAILURE`
- `--compare <path>` flag on `govos score` — compares current scores against a previous score JSON report and emits a delta summary
- `--explain` flag on `govos score` — includes the scoring formula in output
- New modules: `src/governance_os/intelligence/` (priority, scoring, insights, comparison), `src/governance_os/models/score.py`
- 79 new tests (308 total) covering scoring correctness, grade bands, priority classification, all five insight patterns, delta computation, and edge cases

---

## [0.3.0] — 2026-03-25

### Changed

- `govos scan` now exits `1` on parse errors (fail-closed); previously always exited `0`
- `govos status` now raises an explicit `typer.Exit(0)` (reporting command, no pass/fail state)
- `govos registry build` now exits `0`/`1` based on registry errors; previously always exited `0`
- `govos audit readiness/coverage/drift` now exit `0`/`1` based on error-severity findings; previously always exited `0`
- `govos discover candidates` now raises an explicit `typer.Exit(0)` (advisory command)
- `govos doctrine validate` now uses `Issue`-based reporting (code, severity, message) consistent with all other commands
- `validate_doctrine()` return type changed from `list[str]` to `list[Issue]`; now accepts multi-file doctrine packs (all `.md` files in `governance/doctrine/`)
- `audit_coverage` now scans nested directories recursively (previously top-level only)
- `_NO_DEP_TOKENS` extracted to module-level constant in `audit/core.py`; dead no-op inputs check removed
- YAML skill files (`.yaml`/`.yml`) now extract description from `description:` or `name:` fields during skills indexing

### Added

- `ScanResult.passed` property — `True` when no parse errors
- 13 integration tests covering end-to-end workflows: `init→scan→verify→preflight`, `init→registry build→snapshot reconcile`, `audit drift`, `--out` flag, `authority verify`

### Fixed

- Dead code removed from `audit_readiness` (unreachable `if not p.inputs: pass` block)
- `_NO_DEP_TOKENS` was duplicated across two functions in `audit/core.py`; now a single module-level constant

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
