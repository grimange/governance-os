# Release Operations

Operational guide for maintainers covering CI, release triggering, automation
validation steps, and publish configuration.

---

## CI overview

Two workflows run on every push to `main` and every pull request:

### `.github/workflows/ci.yml`

| Job | What it does |
|-----|--------------|
| `test` | Installs from editable source, runs full pytest suite with coverage (Python 3.11 and 3.12) |
| `lint` | Runs Ruff (lint) and Black (format check) |
| `build-check` | Builds sdist + wheel with `python -m build`, installs the wheel in a clean venv, verifies CLI entrypoint and version metadata |

All three jobs must pass for a PR to be mergeable.

The `build-check` job validates the **built artifact**, not just the source tree.
It catches packaging errors that editable installs hide (e.g., missing files,
broken entry points, wrong version in wheel metadata).

---

## Release workflow

### `.github/workflows/release.yml`

Triggered by any tag matching `v[0-9]*` pushed to the repository.

```
push tag v0.9.0
       │
       ▼
  validate ──── test suite + version/tag/changelog guard
       │
       ▼
   build ──── python -m build → sdist + wheel → upload as pipeline artifact
       │
       ▼
   smoke ──── download wheel → clean venv → govos --help, govos scan --help, import check
       │
       ▼
github-release ──── extract CHANGELOG section → create GitHub Release → attach dist/*
       │
       ▼
  publish ──── PyPI trusted publishing (OIDC, gated by "pypi" environment)
```

Each stage depends on the previous succeeding. A validation or smoke failure
blocks the release before any artifacts are published.

---

## How to trigger a release

1. Ensure CI is green on `main`.
2. Bump the version in `src/governance_os/version.py` only:
   ```python
   __version__ = "X.Y.Z"
   ```
3. Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md`.
4. Commit both files:
   ```bash
   git add src/governance_os/version.py CHANGELOG.md
   git commit -m "chore: release vX.Y.Z"
   ```
5. Push a signed tag:
   ```bash
   git tag -a "vX.Y.Z" -m "Release vX.Y.Z"
   git push origin main --tags
   ```

The tag push triggers the release workflow automatically.

---

## Release guards

The `validate` job runs these checks before any artifact is built:

| Guard | What fails it |
|-------|---------------|
| Full test suite | Any test failure |
| Tag matches `version.py` | `v0.9.0` tag but `version.py` has `0.8.0` |
| `version.py` matches tag | Same check, both directions |
| CHANGELOG entry present | `## [X.Y.Z]` section missing from `CHANGELOG.md` |

If any guard fails, the workflow aborts before building artifacts.

---

## Smoke validation

The `smoke` job validates the **built wheel** (not the source tree) by:

1. Creating a fresh virtual environment with no project source.
2. Installing only the `.whl` produced by the `build` job.
3. Running `govos --help` — confirms CLI entrypoint is installed.
4. Running `govos scan --help` — confirms sub-command routing works.
5. Running an import check — confirms `governance_os.__version__` matches `importlib.metadata`.

A failure here means the wheel is broken even though tests pass from source.

---

## Publish configuration

### PyPI trusted publishing (OIDC)

The `publish` job uses `pypa/gh-action-pypi-publish` with OIDC authentication.
No API token is stored in GitHub secrets.

**External setup required before first publish:**

1. **GitHub environment**: create an environment named `pypi` in repo Settings →
   Environments. Add required reviewers if you want manual approval before publish.

2. **PyPI trusted publisher**: on PyPI, go to the project's Publishing page and
   add a trusted publisher with:
   - Owner: `grimange`
   - Repository: `governance-os`
   - Workflow: `release.yml`
   - Environment: `pypi`

Once configured, the workflow publishes automatically after a successful
`github-release` step, subject to environment approval rules.

### Permissions

The release workflow uses the minimum required permissions:
- `contents: write` — needed to create the GitHub release and upload assets
- `id-token: write` — needed by the `publish` job for OIDC token exchange

All other permissions default to `read`.

---

## What to check if release automation fails

| Symptom | First check |
|---------|-------------|
| `validate` fails | Run `pytest` locally; check `git tag` matches `version.py` and CHANGELOG |
| `build` fails | Run `pip install build && python -m build` locally; check `dist/` contains both `.whl` and `.tar.gz` |
| `smoke` fails | Install the wheel in a clean venv manually: `pip install dist/*.whl && govos --help` |
| `github-release` fails | Check repo `contents: write` permission is set on the workflow |
| `publish` fails | Check PyPI trusted publisher is configured; check environment name is exactly `pypi` |

---

## Rolling back a bad release

1. **Yank the PyPI release** (marks it unsafe without deleting history):
   ```bash
   pip install twine
   twine yank governance-os X.Y.Z
   ```
2. Fix the issue in a new patch release (`X.Y.Z+1`).
3. Do not delete tags; note the issue in `CHANGELOG.md` under the new release.
