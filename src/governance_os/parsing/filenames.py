"""Filename parsing and pipeline identity extraction for governance-os.

Expected filename convention: ``<id>--<slug>.md``

Examples:
    001--establish-skeleton.md  -> id="001", slug="establish-skeleton"
    042--verify-outputs.md      -> id="042", slug="verify-outputs"

Files that do not match the pattern yield a structured parse failure rather
than a raised exception so callers can collect and report issues uniformly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# id = one or more digits; slug = one or more lowercase-alphanumeric-or-hyphen chars
_PATTERN = re.compile(r"^(?P<id>\d+)--(?P<slug>[a-z0-9][a-z0-9-]*)\.md$")


@dataclass(frozen=True)
class PipelineIdentity:
    """Parsed identity derived from a pipeline filename."""

    numeric_id: str   # zero-padded string, e.g. "001"
    slug: str         # e.g. "establish-skeleton"
    path: Path        # original file path


@dataclass(frozen=True)
class FilenameParseError:
    """Structured failure produced when a filename does not match the convention."""

    path: Path
    reason: str


def parse_filename(path: Path) -> PipelineIdentity | FilenameParseError:
    """Parse pipeline identity from *path*.

    Args:
        path: Path to a candidate pipeline file.

    Returns:
        PipelineIdentity on success, FilenameParseError on failure.
    """
    name = path.name
    match = _PATTERN.match(name)
    if not match:
        return FilenameParseError(
            path=path,
            reason=(
                f"Filename '{name}' does not match the required pattern "
                "'<id>--<slug>.md' (e.g. '001--example-title.md')"
            ),
        )
    return PipelineIdentity(
        numeric_id=match.group("id"),
        slug=match.group("slug"),
        path=path,
    )


def parse_filenames(
    paths: list[Path],
) -> tuple[list[PipelineIdentity], list[FilenameParseError]]:
    """Parse identity from a list of candidate pipeline paths.

    Args:
        paths: Candidate pipeline file paths.

    Returns:
        Tuple of (identities, errors).
    """
    identities: list[PipelineIdentity] = []
    errors: list[FilenameParseError] = []
    for path in paths:
        result = parse_filename(path)
        if isinstance(result, PipelineIdentity):
            identities.append(result)
        else:
            errors.append(result)
    return identities, errors
