# Changelog

All notable changes to governance-os are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [0.9.0] — 2026-03-26

### Added

#### Phase 0 — Contract Foundation

- `contracts/failure_codes.py` — `FailureCode(StrEnum)` with 7 canonical codes: `TOOLING_UNAVAILABLE_FAIL_CLOSED`, `TOOL_POLICY_VIOLATION`, `TOOL_BYPASS_DETECTED`, `SEQUENCE_VIOLATION`, `EVIDENCE_MISSING`, `TEST_EXECUTION_MISSING`, `CONTRACT_INPUT_INVALID`
- `contracts/tool_policy.py` — `ToolPolicy` frozen Pydantic model with built-in policies `READ_ONLY_AUDIT`, `STANDARD_CODE_CHANGE`, `HIGH_ASSURANCE_RELEASE`; `POLICY_REGISTRY` dict
- `contracts/execution_trace.py` — `ExecutionTrace` with `ToolCallRecord`, `FileChangeRecord`; 6-stage `LifecycleStage` progression; `.save()/.load()/.exists()` persistence to `artifacts/governance/mcp-runs/<run_id>/trace.json`; fail-closed mutation guards

#### Phase 1 — Minimal MCP Server

- `govos_get_task_contract` — loads pipeline contract, initialises ExecutionTrace with fresh run_id
- `govos_read_repo_map` — returns all pipeline lifecycle states; advances to CONTEXT_ACQUIRED
- `govos_write_patch` — managed file write with path traversal guard; records FileChangeRecord(via_managed_patch=True)
- `govos_finalize_result` — finalizes trace, runs governance validator, records result
- `mcp/server.py` — FastMCP "governance-os-mcp" registering all 10 tools; `govos-mcp` entry point

#### Phase 2 — Validation Layer

- `runtime/validator.py` — `validate(trace, policy) → ValidationResult`; 6 enforcement rules: required tools, required sequence, unmanaged write detection, finalization, evidence presence, test execution

#### Phase 3 — Codex Integration

- `.codex/config.toml` — MCP server registration, approval posture (require_approval_for file_write/shell_exec/git_write), default policy mode
- `.codex/rules.toml` — rules restricting unmanaged writes, destructive git operations, arbitrary shell, direct patch application

#### Phase 4 — Tool Surface Expansion

- `govos_search_code` — bounded regex file search (no shell invocation)
- `govos_get_file_context` — read-only file context with path traversal guard and line-range slicing
- `govos_run_tests` — bounded pytest execution (restricted flags allowlist); advances to VERIFICATION_COMPLETED
- `govos_run_lint` — bounded ruff check execution
- `govos_record_evidence` — evidence reference recording; rejects empty refs and finalized runs; advances to EVIDENCE_RECORDED
- `govos_git_status` — read-only git status + branch; bounded to `git status --short` only

#### Phase 5 — Lifecycle Integration

- Trace persistence at `artifacts/governance/mcp-runs/<run_id>/` aligns with v0.8 pipeline lifecycle marker convention
- `govos_read_repo_map` exposes full pipeline lifecycle state (effective_state, drift, reasons) to MCP agents

#### Tests

- `tests/test_contracts.py` — 37 tests: FailureCode, ToolPolicy, built-in policies, ExecutionTrace, lifecycle, persistence
- `tests/test_validator.py` — 30 tests: all 6 validator rules (pass + fail), full-run integration scenarios
- `tests/test_mcp_tools.py` — 33 tests: all Phase 1/4 tools, path traversal rejection, finalization guards, MCP server registration

### Changed

- `pyproject.toml` — added `mcp = ["mcp>=1.0.0"]` optional dependency; `govos-mcp` script entry point

---

## [0.8.0] — 2026-03-26

### Added

- **Pipeline lifecycle state machine** — 7 canonical states: `draft`, `ready`, `active`, `blocked`, `completed`, `failed`, `archived`; deterministic, fully explainable inference with no side effects
- **`Pipeline.declared_state`** — new optional field populated from `State:` or `Lifecycle State:` in pipeline contracts; empty string when absent
- **`State:` / `Lifecycle State:` parser support** — `markdown_contract.py` extended to recognise inline (`State: active`) and heading-style (`### Lifecycle State\ncompleted`) forms
- **Marker file protocol** — three filesystem markers drive runtime inference: `artifacts/governance/failures/<id>.md` → FAILED; `artifacts/governance/blocks/<id>.md` → BLOCKED (external); `artifacts/governance/runs/<id>/` directory → ACTIVE
- **`classify_lifecycle(pipelines, root, extra_issues)` → `LifecycleResult`** — core inference engine in `lifecycle/core.py`; uses iterative topological passes to propagate dependency state; unresolved cycles → BLOCKED
- **`lifecycle_issues(result)` → `list[Issue]`** — derives `LIFECYCLE_DRIFT` (WARNING), `LIFECYCLE_FAILED` (ERROR), `LIFECYCLE_INVALID_DECLARED_STATE` (WARNING) Issue records from a LifecycleResult for integration with audit/preflight
- **`LifecycleResult`** model — aggregated lifecycle report; `.active`, `.blocked`, `.failed`, `.completed`, `.draft`, `.ready`, `.drifted` convenience properties
- **`LifecycleRecord`** model (frozen) — per-pipeline record: `pipeline_id`, `slug`, `path`, `declared_state`, `effective_state`, `drift`, `reasons`
- **Drift detection** — `drift=True` when `declared_state` is a recognised value and differs from `effective_state`; unrecognised declared values are flagged as `LIFECYCLE_INVALID_DECLARED_STATE` but not counted as drift
- **`api.pipeline_lifecycle(root, config)` → `LifecycleResult`** — classifies all pipelines
- **`api.pipeline_lifecycle_status(root, pipeline_id, config)` → `LifecycleRecord | None`** — returns record for a single pipeline by numeric ID or slug
- **`govos pipeline list [PATH] [--json]`** — lists all pipelines with effective lifecycle state and drift markers
- **`govos pipeline status <id> [--root PATH] [--json]`** — shows effective state, declared state, drift, and reasons for one pipeline
- **`govos pipeline verify <id> [--root PATH]`** — exits 0 if lifecycle state is consistent, 1 if drift detected
- **Console formatters** `format_lifecycle()` and `format_lifecycle_record()` in `reporting/console.py`
- **JSON serialisers** `lifecycle_to_json()` and `lifecycle_record_to_json()` in `reporting/json_report.py`
- 57 new tests covering all 7 lifecycle states, marker file behavior, dep propagation, drift detection, parser extension, API functions, console formatting, JSON output (519 total)

### Inference priority order (deterministic)
1. Failure marker → FAILED (objective filesystem evidence, overrides declared)
2. Declared `archived` → ARCHIVED (author-terminal)
3. Declared `completed` → COMPLETED (author-terminal)
4. Block marker → BLOCKED (external block)
5. Schema errors → DRAFT (contract not ready)
6. Blocking dependency (DRAFT/BLOCKED/FAILED dep) → BLOCKED (propagated)
7. Run directory marker → ACTIVE (execution in progress)
8. No blockers → READY

---

## [0.7.0] — 2026-03-26

### Added

- `govos init --profile codex --template multi-agent` — scaffolds role-specialized multi-agent Codex structure: `.codex/agents/` role definitions (planner, implementer, reviewer), `docs/governance/agents/` role contracts, `docs/contracts/multi-agent-workflow.md`, and `artifacts/governance/handoffs/` + `artifacts/governance/reviews/` artifact directories; extends the `governed` template
- `govos audit multi-agent [PATH] [--json] [--out]` — audits multi-agent setup for structural completeness; checks role definitions, role contracts, workflow contract, artifact directories; missing reviewer emits ERROR, other gaps emit WARNING, missing artifact dirs emit INFO
- `MultiAgentPlugin` (`plugin_id = "multi_agent"`) — wraps `audit_multi_agent`; not in any default_plugins; activate via `enabled_plugins: [multi_agent]` in governance.yaml; automatically enabled by `govos init --template multi-agent`
- `audit_multi_agent(root)` function in `audit/core.py` — 9 finding codes: `MULTIAGENT_SETUP_MISSING`, `MULTIAGENT_MISSING_ROLE_DEF`, `MULTIAGENT_MISSING_REVIEWER` (ERROR), `MULTIAGENT_MISSING_ROLE_CONTRACT`, `MULTIAGENT_EMPTY_ROLE_CONTRACT`, `MULTIAGENT_ROLE_MISMATCH`, `MULTIAGENT_MISSING_WORKFLOW`, `MULTIAGENT_MISSING_HANDOFFS_DIR`, `MULTIAGENT_MISSING_REVIEWS_DIR`
- `multi-agent` added to CODEX profile `supported_templates`; displayed by `govos profile show codex`
- `_governance_yaml()` extended with `template` parameter — `multi-agent` template writes `enabled_plugins: [multi_agent]` to generated `governance.yaml`
- 39 new tests covering scaffold generation, role definition content, role contract content, workflow contract, audit checks for all 9 finding codes, plugin registration, plugin preflight integration (457 total)

### Changed

- `api.audit()` dispatcher now supports `"multi-agent"` mode (raises `ValueError` for unknown modes as before)
- README updated with `codex:multi-agent` scaffold layout, `govos audit multi-agent` documentation, and plugin activation instructions

---

## [0.6.0] — 2026-03-26

### Added

- `govos init --template minimal|governed` — new primary flag for scaffold surface area selection; `--level` retained for backward compatibility; `--template` takes precedence when both are given
- **`codex:minimal` scaffold** — `AGENTS.md` (short, operational), `.codex/config.toml` (governance profile config), `governance/sessions/`, `governance.yaml` with `profile: codex`
- **`codex:governed` scaffold** — above plus `governance/skills/govos-preflight.skill.md`, `governance/doctrine/`, `docs/governance/`, `artifacts/governance/`; authored skill contains preflight procedure so AGENTS.md stays concise
- **`generic:minimal` and `generic:governed` scaffold** — governed variant now correctly generates `governance.yaml` with `authority:`, `registry:`, and `audit:` sections (bug fix: these were previously silently skipped due to overwrite guard)
- `governance.yaml` generated by `govos init` now always includes a `profile:` field set to the active profile
- `ProfileDefinition.supported_templates` field — exposes available templates per profile; displayed by `govos profile list` and `govos profile show`
- `ScaffoldResult.template` field — records the effective template used during init
- 40 new tests covering all four profile × template combinations, `.codex/config.toml` content, skill file content, governance.yaml sections, invalid template rejection, backward-compat level flag, and idempotency (418 total)

### Changed

- `govos profile list` now shows `templates:` line per profile
- `govos profile show` now shows `Supported templates:` field
- `format_result()` output now shows `profile=X  template=Y` (previously `level=X  profile=Y`)
- README updated with scaffold combinations table, profile × template matrix, and updated `govos init` CLI reference

### Fixed

- `govos init --level governed` (and `--template governed`) now correctly writes governed `governance.yaml` content; previously the governed config was silently skipped because `_write_file()` refused to overwrite the minimal config already written earlier in the same call

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
