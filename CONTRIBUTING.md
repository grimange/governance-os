# Contributing to governance-os

## Getting started

```
git clone <repo>
cd governance-os
pip install -e ".[dev]"
pytest
```

## Development workflow

1. Create a branch from `main`.
2. Make your changes.
3. Run the test suite: `pytest`
4. Run lint checks: `ruff check src/ tests/`
5. Run formatting check: `black --check src/ tests/`
6. Open a pull request against `main`.

## Code style

- Formatter: [Black](https://black.readthedocs.io/) (line length 100)
- Linter: [Ruff](https://docs.astral.sh/ruff/)
- Type hints are required for all public functions.
- Pydantic models are used at all data boundaries.

## Tests

All changes must be covered by tests. Tests live in `tests/` and mirror the module structure under `src/`.

```
pytest                               # run all tests
pytest --cov=governance_os           # with coverage
pytest tests/test_cli.py             # single file
```

## Issue codes

Issue codes (e.g. `MISSING_REQUIRED_FIELD`, `UNRESOLVED_DEPENDENCY`) are part of the public contract. Changing or removing a code is a breaking change — add a new code instead.

## Commit messages

Use the imperative mood in the subject line (e.g. "Add portability check for tilde paths"). Keep the subject under 72 characters.

## Reporting bugs

Open an issue at the project bug tracker. Include:
- governance-os version (`govos --version` or `pip show governance-os`)
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behaviour
