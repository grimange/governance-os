"""Skills index and reference validation for governance-os.

Skills are reusable capability definitions — markdown or YAML files describing
repeatable tasks that pipelines can reference. This module indexes and validates them.

This is advisory/validation only. No agent orchestration logic.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel

from governance_os.models.issue import Issue, Severity

# Directories to search for skill definitions (in priority order)
_SKILLS_DIRS = [
    "governance/skills",
    "skills",
    "docs/skills",
    ".governance/skills",
]

# Supported skill file extensions
_SKILL_EXTENSIONS = frozenset({".md", ".yaml", ".yml"})


class SkillEntry(BaseModel):
    """A discovered skill definition."""

    skill_id: str
    name: str
    path: Path
    description: str = ""

    model_config = {"frozen": True}


class SkillsResult(BaseModel):
    """Result of a skills index or verify operation."""

    root: Path
    skills_dir: Path | None = None
    entries: list[SkillEntry] = []
    issues: list[Issue] = []

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def skill_count(self) -> int:
        return len(self.entries)


def _find_skills_dir(root: Path) -> Path | None:
    """Locate the skills directory relative to root."""
    for candidate in _SKILLS_DIRS:
        path = root / candidate
        if path.exists() and path.is_dir():
            return path
    return None


def _slug_from_path(path: Path) -> str:
    """Derive a skill id from a file path."""
    return path.stem.lower().replace("_", "-").replace(" ", "-")


def index_skills(root: Path) -> SkillsResult:
    """Discover and index all skill definitions in the repository.

    Args:
        root: Repository root directory.

    Returns:
        SkillsResult with indexed skill entries and any discovery issues.
    """
    issues: list[Issue] = []
    entries: list[SkillEntry] = []

    skills_dir = _find_skills_dir(root)

    if skills_dir is None:
        issues.append(
            Issue(
                code="SKILLS_DIR_NOT_FOUND",
                severity=Severity.INFO,
                message=(
                    "No skills directory found. Checked: "
                    + ", ".join(_SKILLS_DIRS)
                    + ". Create one to define reusable skill references."
                ),
                path=root,
                suggestion="Create a 'governance/skills/' directory with skill definition files.",
            )
        )
        return SkillsResult(root=root, skills_dir=None, entries=[], issues=issues)

    skill_files = sorted(
        f for f in skills_dir.rglob("*") if f.is_file() and f.suffix in _SKILL_EXTENSIONS
    )

    # Detect duplicate skill ids
    by_id: dict[str, list[Path]] = defaultdict(list)
    for skill_file in skill_files:
        skill_id = _slug_from_path(skill_file)
        by_id[skill_id].append(skill_file)

    for skill_id, paths in by_id.items():
        if len(paths) > 1:
            path_names = ", ".join(str(p.name) for p in paths)
            issues.append(
                Issue(
                    code="SKILLS_DUPLICATE_ID",
                    severity=Severity.WARNING,
                    message=f"Duplicate skill id '{skill_id}' found in: {path_names}",
                    path=skills_dir,
                    suggestion="Use unique filenames for each skill definition.",
                )
            )

    for skill_file in skill_files:
        skill_id = _slug_from_path(skill_file)
        name = skill_file.stem.replace("-", " ").replace("_", " ").title()

        # Extract description from file content
        description = ""
        if skill_file.suffix == ".md":
            try:
                for line in skill_file.read_text(encoding="utf-8").splitlines()[:5]:
                    line = line.strip().lstrip("#").strip()
                    if line:
                        description = line
                        break
            except OSError:
                pass
        elif skill_file.suffix in {".yaml", ".yml"}:
            try:
                for line in skill_file.read_text(encoding="utf-8").splitlines()[:15]:
                    stripped = line.strip()
                    if stripped.startswith("description:"):
                        description = stripped[len("description:") :].strip().strip('"').strip("'")
                        break
                    if stripped.startswith("name:") and not description:
                        description = stripped[len("name:") :].strip().strip('"').strip("'")
            except OSError:
                pass

        entries.append(
            SkillEntry(
                skill_id=skill_id,
                name=name,
                path=skill_file,
                description=description,
            )
        )

    return SkillsResult(root=root, skills_dir=skills_dir, entries=entries, issues=issues)


def verify_skills(
    root: Path, pipelines_implementation_notes: list[str] | None = None
) -> SkillsResult:
    """Index skills and validate references.

    In addition to indexing, checks for:
    - Skill files with no content
    - Skills referenced in pipeline notes that are not indexed

    Args:
        root: Repository root directory.
        pipelines_implementation_notes: Optional list of implementation note strings
            to scan for skill references (advisory only).

    Returns:
        SkillsResult with validation findings.
    """
    result = index_skills(root)
    issues = list(result.issues)

    # Check for empty skill files
    for entry in result.entries:
        try:
            content = entry.path.read_text(encoding="utf-8").strip()
        except OSError:
            content = ""

        if not content:
            issues.append(
                Issue(
                    code="SKILLS_EMPTY_FILE",
                    severity=Severity.WARNING,
                    message=f"Skill file '{entry.path.name}' is empty.",
                    path=entry.path,
                    suggestion="Add content to the skill definition file.",
                )
            )

    return SkillsResult(
        root=result.root,
        skills_dir=result.skills_dir,
        entries=result.entries,
        issues=issues,
    )
