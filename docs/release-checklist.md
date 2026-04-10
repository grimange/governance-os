# Release Checklist

Operational checklist for publishing a new governance-os release.

Steps 1–3 are manual. Steps 4–7 are automated by the release workflow
(`.github/workflows/release.yml`) once the tag is pushed.

See `docs/release-operations.md` for full CI/release automation details.

---

## Before you start

- [ ] All planned work for the release is merged to `main`
- [ ] CI is green on `main` (test, lint, and build-check jobs all pass)

---

## 1. Bump the version

Edit **one file only** — `src/governance_os/version.py`:

```python
__version__ = "X.Y.Z"
```

`pyproject.toml` reads from this file via `[tool.hatch.version]`.
`governance_os.__version__` imports from this file directly.
No other version surfaces need manual edits.

---

## 2. Update the changelog

In `CHANGELOG.md`, add a new section above the previous release:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added / Changed / Fixed / Removed
- ...
```

The release workflow checks that this section exists. Missing it blocks the release.

---

## 3. Commit and push tag

```bash
git add src/governance_os/version.py CHANGELOG.md
git commit -m "chore: release vX.Y.Z"
git tag -a "vX.Y.Z" -m "Release vX.Y.Z"
git push origin main --tags
```

Pushing the tag triggers the release workflow automatically.

---

## 4–7. Automated steps (release workflow)

After the tag push, the workflow runs:

| Step | What happens |
|------|--------------|
| `validate` | Full test suite + version/tag/changelog consistency check |
| `build` | `python -m build` → sdist + wheel |
| `smoke` | Install wheel in clean venv → `govos --help`, import check |
| `github-release` | Creates GitHub Release, attaches sdist and wheel |
| `publish` | Publishes to PyPI via OIDC trusted publishing (requires "pypi" environment) |

Monitor the workflow at: `https://github.com/grimange/governance-os/actions`

---

## 8. Verify the release

- [ ] All release workflow jobs are green
- [ ] GitHub Release page shows correct version and attached artifacts
- [ ] PyPI page shows correct version, description, and URLs
- [ ] `pip install governance-os==X.Y.Z` installs successfully
- [ ] `govos --version` or `govos --help` returns the expected version

---

## Rollback

If a bad release is caught post-publish:

1. Yank the PyPI release (marks it unsafe without deleting history):
   ```bash
   pip install twine
   twine yank governance-os X.Y.Z
   ```
2. Fix the issue in a new patch release (`X.Y.Z+1`).
3. Do not delete tags; add a note to `CHANGELOG.md` under the new release.
