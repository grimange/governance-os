# Testing Strategy

This document describes how the governance-os test suite is organized, what
kinds of promises are protected by each layer, and how to maintain the suite
as the product evolves.

---

## Test layers

### Unit tests (most test files)

Test internal logic in isolation — parsers, models, graph algorithms, scoring
formulas, report serialization. Fast, numerous, and focused on correctness of
individual components.

**Examples:** `test_validation.py`, `test_lifecycle.py`, `test_scoring.py`,
`test_portability.py`, `test_graph.py`

### Contract/golden tests

Protect explicitly promised behavior that must not change silently. These tests
encode what the product guarantees, not how it implements them.

**Primary contract file:** `test_governance_contract.py`
- JSON output schema: all `--json` outputs include `schema_version`, `command`, `root`, `passed`
- Exit code contract: 0 = pass, 1 = governance failure, 2 = usage error
- Severity semantics: ERROR blocks (exit 1), WARNING/INFO are advisory (exit 0)
- Fail-closed behavior: invalid profiles, bad templates, missing pipelines → exit 2

When a contract changes intentionally, update both the implementation and the
corresponding contract test in the same commit.

### Product promise tests

`test_product_promises.py` fills the gap between unit tests and the contract
layer: CLI flags, command option behavior, and documented flows that were
untested at the CLI level.

**Coverage targets:**
- `govos init --dry-run` — preview without writing; `--force` — overwrite
- `govos audit *` exit codes per mode
- `govos preflight --authority` and `--no-portability` flags
- `govos score --compare` and `--explain`
- `govos profile list/validate`, `govos pipeline list/status/verify`
- `govos plugin list/show`
- Multi-agent init → scan → verify → audit workflow
- Package surface: `governance_os.__version__`, `api.*` public functions, CLI help

### Integration tests

`test_integration.py` and `test_multi_agent.py` exercise realistic multi-step
workflows: init a repo, add content, run several commands, verify the chain.

### Extension architecture tests

`test_extension_architecture.py` protects the profile/plugin registry
boundaries: known profiles, known plugins, `validate_plugin_ids()` behavior,
CLI commands for `plugin` and `profile` sub-apps.

---

## What belongs where

| Test kind | Belongs in |
|-----------|------------|
| A parser or model returns the right value | Unit test file for that module |
| A CLI command exits with the documented code | `test_governance_contract.py` or `test_product_promises.py` |
| A documented `--flag` works as described | `test_product_promises.py` |
| A stable JSON field is present in `--json` output | `test_governance_contract.py` |
| A multi-step user workflow succeeds end-to-end | `test_integration.py` |
| A profile or plugin is registered correctly | `test_extension_architecture.py` |

---

## Golden/contract test maintenance

Contract tests protect promises. When a promise changes intentionally:

1. Update the implementation.
2. Update the contract test to match the new promise.
3. Commit both in the same change, with a comment in the test explaining the
   new behavior.

Do not update a contract test to make a test pass without also updating the
documentation that describes the promise.

---

## Fixtures

All CLI tests use `typer.testing.CliRunner` with `tmp_path` (pytest's
deterministic temp directory). The `_init_standard(tmp_path)` helper in
`test_product_promises.py` creates a minimal valid repo with one parseable
pipeline.

Prefer explicit inline file writes over shared fixtures — they make test intent
clear without hidden setup.

---

## Performance

The test suite runs in under 3 seconds. To keep it that way:
- Avoid actual subprocess invocations; use `CliRunner` instead.
- Avoid network calls.
- Avoid large fixture files.
- Do not add sleep or retry logic.
