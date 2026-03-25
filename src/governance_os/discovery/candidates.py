"""Contract-candidate discovery for governance-os.

Identifies likely pipeline surfaces in a repository that do not yet have
governance contracts. All suggestions are advisory — no files are written.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from governance_os.models.pipeline import Pipeline

# Directories to skip during candidate scanning
_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".github",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        ".tox",
        ".mypy_cache",
        "site-packages",
        "artifacts",
        "docs",
    }
)

# Files whose presence strongly suggests a pipeline surface
_HIGH_CONFIDENCE = frozenset(
    {
        "Makefile",
        "makefile",
        "build.sh",
        "deploy.sh",
        "release.sh",
        "Dockerfile",
        "Jenkinsfile",
    }
)

# Files that suggest a moderate-confidence pipeline surface
_MEDIUM_CONFIDENCE = frozenset(
    {
        "run.sh",
        "pipeline.yaml",
        "pipeline.yml",
        "workflow.yaml",
        "workflow.yml",
        "docker-compose.yaml",
        "docker-compose.yml",
        ".buildkite",
        "circle.yml",
        ".travis.yml",
        "tox.ini",
        "setup.py",
        "setup.cfg",
    }
)


class Candidate(BaseModel):
    """A suggested contract candidate."""

    path: Path
    suggested_id: str | None = None
    confidence: str  # "high", "medium", "low"
    reason: str

    model_config = {"frozen": True}


class CandidateResult(BaseModel):
    """Result of a contract-candidate discovery scan."""

    root: Path
    candidates: list[Candidate] = []

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    def by_confidence(self, level: str) -> list[Candidate]:
        return [c for c in self.candidates if c.confidence == level]


def _next_available_id(existing_ids: set[str], start: int = 1) -> str:
    """Find the next available 3-digit numeric id."""
    n = start
    while True:
        candidate_id = f"{n:03d}"
        if candidate_id not in existing_ids:
            return candidate_id
        n += 1


def discover_candidates(root: Path, pipelines: list[Pipeline]) -> CandidateResult:
    """Discover likely pipeline-candidate directories in the repository.

    Scans for directories containing pipeline-indicator files that are not
    already covered by a governance contract.

    Args:
        root: Repository root directory.
        pipelines: Currently contracted pipelines.

    Returns:
        CandidateResult with suggested contract candidates.
    """
    contracted_slugs = {p.slug for p in pipelines}
    existing_ids = {p.numeric_id for p in pipelines}
    candidates: list[Candidate] = []
    next_id_counter = 1

    # Scan top-level and one level deep
    dirs_to_check: list[Path] = []

    if root.exists():
        for child in sorted(root.iterdir()):
            if child.is_dir() and child.name not in _IGNORED_DIRS and not child.name.startswith("."):
                dirs_to_check.append(child)

    # Also check .github/workflows
    workflows_dir = root / ".github" / "workflows"
    if workflows_dir.exists():
        dirs_to_check.append(workflows_dir)

    for directory in dirs_to_check:
        slug_like = directory.name.lower().replace("_", "-").replace(" ", "-")

        # Skip if already contracted
        if slug_like in contracted_slugs:
            continue

        # Check confidence level
        confidence = None
        reason = None

        children = set()
        try:
            children = {f.name for f in directory.iterdir() if f.is_file()}
        except PermissionError:
            continue

        high_hits = children & _HIGH_CONFIDENCE
        medium_hits = children & _MEDIUM_CONFIDENCE

        if high_hits:
            confidence = "high"
            reason = f"Contains {sorted(high_hits)[0]} — likely a pipeline surface."
        elif medium_hits:
            confidence = "medium"
            reason = f"Contains {sorted(medium_hits)[0]} — possibly a pipeline surface."
        elif len(children) >= 5:
            # Large directories with many files may warrant coverage
            confidence = "low"
            reason = f"Directory has {len(children)} files — may be a pipeline surface worth contracting."

        if confidence is not None:
            suggested_id = _next_available_id(existing_ids, next_id_counter)
            existing_ids.add(suggested_id)
            next_id_counter = int(suggested_id) + 1

            candidates.append(
                Candidate(
                    path=directory,
                    suggested_id=suggested_id,
                    confidence=confidence,
                    reason=reason,
                )
            )

    # Also check for pyproject.toml / package.json at root — indicates the root itself is a pipeline
    root_indicators = {"pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml"}
    root_children = {f.name for f in root.iterdir() if f.is_file()} if root.exists() else set()
    root_hits = root_children & root_indicators

    if root_hits and "root" not in contracted_slugs:
        suggested_id = _next_available_id(existing_ids, next_id_counter)
        candidates.append(
            Candidate(
                path=root,
                suggested_id=suggested_id,
                confidence="medium",
                reason=f"Repo root contains {sorted(root_hits)[0]} — the root package may warrant a governance contract.",
            )
        )

    return CandidateResult(root=root, candidates=candidates)
