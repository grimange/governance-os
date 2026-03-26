"""Markdown contract parser for governance-os pipeline files.

Parses non-frontmatter markdown pipeline contracts into structured data.
Uses markdown-it-py for token-level parsing rather than line-by-line regex.

Expected document shape::

    # <numeric-id> — <title>

    Stage: <value>

    Purpose:
    <text>

    Depends on:
    - <item>

    Inputs:
    - <item>

    Outputs:
    - <item>

    Implementation Notes:
    <text>

    Success Criteria:
    - <item>

    Out of Scope:
    - <item>

Sections may also use heading syntax (``### Stage\\n<value>``) as produced
by the pipeline pack itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

# Canonical label → field name mapping (labels normalised to lower-case).
_LABEL_MAP: dict[str, str] = {
    "stage": "stage",
    "scope": "scope",
    "purpose": "purpose",
    "depends on": "depends_on",
    "inputs": "inputs",
    "outputs": "outputs",
    "implementation notes": "implementation_notes",
    "success criteria": "success_criteria",
    "out of scope": "out_of_scope",
    # Lifecycle fields
    "state": "declared_state",
    "lifecycle state": "declared_state",
}

_md = MarkdownIt()


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ParsedContract:
    """Parsed content of a pipeline contract file."""

    path: Path
    title: str = ""
    stage: str = ""
    scope: str = ""
    purpose: str = ""
    depends_on: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    implementation_notes: str = ""
    success_criteria: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    declared_state: str = ""
    issues: list[ParseIssue] = field(default_factory=list)


@dataclass(frozen=True)
class ParseIssue:
    """A non-fatal problem detected during parsing."""

    path: Path
    code: str
    message: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _inline_text(tokens: list[Token], idx: int) -> str:
    """Return the content of the inline token at idx+1 (after an _open token)."""
    if idx + 1 < len(tokens) and tokens[idx + 1].type == "inline":
        return tokens[idx + 1].content
    return ""


def _resolve_label(raw: str) -> str | None:
    """Normalise *raw* and return the field name, or None if unrecognised."""
    key = raw.strip().rstrip(":").strip().lower()
    return _LABEL_MAP.get(key)


def _extract_list_items(tokens: list[Token], start: int) -> tuple[list[str], int]:
    """Extract text items from a bullet_list block starting at *start*.

    Returns (items, index_after_list_close).
    """
    items: list[str] = []
    i = start + 1  # skip bullet_list_open
    depth = 1
    while i < len(tokens) and depth > 0:
        t = tokens[i]
        if t.type == "bullet_list_open":
            depth += 1
        elif t.type == "bullet_list_close":
            depth -= 1
        elif t.type == "inline" and depth == 1:
            text = t.content.strip()
            if text:
                items.append(text)
        i += 1
    return items, i


def _set_field(contract: ParsedContract, field_name: str, value: object) -> None:
    """Assign *value* to the named field on *contract*."""
    setattr(contract, field_name, value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_contract(path: Path, source: str | None = None) -> ParsedContract:
    """Parse a pipeline contract file into a ParsedContract.

    Args:
        path: Path to the contract file.
        source: Raw markdown source. If None, the file is read from *path*.

    Returns:
        ParsedContract, possibly with attached ParseIssues for missing sections.
    """
    if source is None:
        source = path.read_text(encoding="utf-8")

    contract = ParsedContract(path=path)
    tokens = _md.parse(source)

    # Walk top-level tokens with index so we can lookahead.
    i = 0
    pending_label: str | None = None  # field name waiting for next content block

    while i < len(tokens):
        t = tokens[i]

        # ---- H1 heading → title ----------------------------------------
        if t.type == "heading_open" and t.tag == "h1":
            text = _inline_text(tokens, i)
            contract.title = text.strip()
            i += 3  # heading_open, inline, heading_close
            continue

        # ---- H2/H3 heading → treat as section label --------------------
        if t.type == "heading_open" and t.tag in ("h2", "h3"):
            text = _inline_text(tokens, i)
            field_name = _resolve_label(text)
            if field_name:
                pending_label = field_name
            i += 3
            continue

        # ---- Paragraph → may be inline metadata or a section label -----
        if t.type == "paragraph_open":
            text = _inline_text(tokens, i)

            # "Stage: value" style — inline single-line metadata.
            if ":" in text and "\n" not in text:
                raw_key, _, raw_val = text.partition(":")
                field_name = _resolve_label(raw_key)
                if field_name:
                    val = raw_val.strip()
                    if val:
                        # Value present on the same line.
                        current = getattr(contract, field_name, None)
                        if isinstance(current, list):
                            if val.lower() != "none":
                                _set_field(contract, field_name, [val])
                        else:
                            _set_field(contract, field_name, val)
                        pending_label = None
                    else:
                        # "Key:" with no value — content follows in next block.
                        pending_label = field_name
                    i += 3
                    continue

            # "Purpose:\nSome text." style — label + body in one paragraph.
            if "\n" in text:
                first_line, _, rest = text.partition("\n")
                field_name = _resolve_label(first_line)
                if field_name:
                    body = rest.strip()
                    current = getattr(contract, field_name, None)
                    if isinstance(current, list):
                        items = [ln.lstrip("-* ").strip() for ln in body.splitlines() if ln.strip()]
                        _set_field(contract, field_name, items)
                    else:
                        _set_field(contract, field_name, body)
                    pending_label = None
                    i += 3
                    continue

            # Plain label paragraph ("Depends on:") — content follows.
            field_name = _resolve_label(text)
            if field_name:
                pending_label = field_name
            elif pending_label:
                # The paragraph IS the body for the pending label.
                current = getattr(contract, pending_label, None)
                if isinstance(current, list):
                    items = [ln.lstrip("-* ").strip() for ln in text.splitlines() if ln.strip()]
                    _set_field(contract, pending_label, items)
                else:
                    _set_field(contract, pending_label, text.strip())
                pending_label = None
            i += 3
            continue

        # ---- Bullet list → content for the pending label ----------------
        if t.type == "bullet_list_open":
            items, next_i = _extract_list_items(tokens, i)
            if pending_label:
                current = getattr(contract, pending_label, None)
                if isinstance(current, list):
                    _set_field(contract, pending_label, items)
                else:
                    _set_field(contract, pending_label, "\n".join(items))
                pending_label = None
            i = next_i
            continue

        i += 1

    # ---- Issue reporting for missing required sections ------------------
    required = {
        "title": "Missing H1 title",
        "stage": "Missing 'Stage:' field",
        "purpose": "Missing 'Purpose' section",
        "outputs": "Missing 'Outputs' section",
        "success_criteria": "Missing 'Success Criteria' section",
    }
    for fname, message in required.items():
        val = getattr(contract, fname)
        if not val:
            contract.issues.append(
                ParseIssue(path=path, code=f"MISSING_{fname.upper()}", message=message)
            )

    return contract
