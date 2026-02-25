"""Validate Obsidian note frontmatter against known schemas.

Schemas are derived from the canonical builders in ``note_builder.py``.
Unknown note types or files without frontmatter pass silently (permissive).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

# Characters that break filenames when used in note titles.
# / is a directory separator on POSIX; \ on Windows; others break shells.
_UNSAFE_FILENAME_CHARS = r'/\:*?"<>|'


def sanitize_title(title: str) -> str:
    """Replace filesystem-unsafe characters in a note title with hyphens.

    Prevents accidental directory creation when titles like ``APP/PS1``
    are used as filenames.

    >>> sanitize_title("APP/PS1 mice")
    'APP-PS1 mice'
    >>> sanitize_title("AhR/NF-kappaB/NLRP3")
    'AhR-NF-kappaB-NLRP3'
    """
    for ch in _UNSAFE_FILENAME_CHARS:
        title = title.replace(ch, "-")
    return title


def validate_filename(file_path: str) -> list[str]:
    """Check a file path for unsafe characters in the filename component.

    Returns a list of error strings (empty if valid).
    """
    errors: list[str] = []
    # Extract just the filename (last component)
    # Use rfind to handle paths correctly
    last_sep = file_path.replace("\\", "/").rfind("/")
    filename = file_path[last_sep + 1 :] if last_sep >= 0 else file_path
    for ch in _UNSAFE_FILENAME_CHARS:
        if ch == "/" or ch == "\\":
            # These can't appear in the filename component extracted above
            continue
        if ch in filename:
            errors.append(
                f"Filename contains unsafe character '{ch}': {filename}. "
                f"Use sanitize_title() to replace with '-'."
            )
    return errors


# Reuse the frontmatter regex from hypothesis_parser.py
_FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# ---------------------------------------------------------------------------
# Schema definitions -- required fields per note type
# ---------------------------------------------------------------------------
# Each entry maps a note ``type`` value to its list of required frontmatter
# field names.  Derived from ``note_builder.py`` builder function signatures
# and the frontmatter dicts they produce.

_SCHEMAS: dict[str, list[str]] = {
    "hypothesis": [
        "title",
        "id",
        "status",
        "elo",
        "created",
        "updated",
    ],
    "literature": [
        "title",
        "status",
        "created",
    ],
    "experiment": [
        "title",
        "status",
        "created",
    ],
    "eda-report": [
        "title",
        "dataset",
        "created",
    ],
    "research-goal": [
        "title",
        "status",
        "created",
    ],
    "tournament-match": [
        "date",
        "research_goal",
        "hypothesis_a",
        "hypothesis_b",
    ],
    "meta-review": [
        "date",
        "research_goal",
    ],
    "project": [
        "title",
        "project_tag",
        "lab",
        "status",
        "project_path",
        "created",
        "updated",
    ],
    "lab": [
        "lab_slug",
        "pi",
        "created",
        "updated",
    ],
    "foreign-hypothesis": [
        "title",
        "id",
        "status",
        "elo_federated",
        "elo_source",
        "matches_federated",
        "matches_source",
        "source_vault",
        "imported",
    ],
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of validating a note against its schema."""

    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_note(
    content: str,
    note_type: str | None = None,
) -> ValidationResult:
    """Validate a note's frontmatter against known schemas.

    Args:
        content: Raw markdown content (may or may not have frontmatter).
        note_type: Override the ``type`` field from frontmatter.  When
            provided, the note is validated against this type's schema
            regardless of what ``type`` says in the frontmatter.

    Returns:
        A ``ValidationResult``.  ``valid=True`` when:
        - the content has no YAML frontmatter (not a structured note),
        - the frontmatter has no ``type`` field and no *note_type* override,
        - the type is not in the known schema registry.

        ``valid=False`` only when a known-type note is missing required
        fields defined in the schema.
    """
    if not content or not content.strip():
        return ValidationResult(valid=True)

    match = _FM_PATTERN.match(content)
    if not match:
        return ValidationResult(valid=True)

    fm_text = match.group(1)
    try:
        frontmatter = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return ValidationResult(valid=False, errors=["Invalid YAML frontmatter"])

    if not isinstance(frontmatter, dict):
        return ValidationResult(valid=True)

    effective_type = note_type or frontmatter.get("type")
    if effective_type is None:
        return ValidationResult(valid=True)

    schema = _SCHEMAS.get(effective_type)
    if schema is None:
        # Unknown type -- pass permissively
        return ValidationResult(valid=True)

    errors: list[str] = []
    for field_name in schema:
        if field_name not in frontmatter:
            errors.append(f"Missing required field: {field_name}")

    if errors:
        return ValidationResult(valid=False, errors=errors)

    return ValidationResult(valid=True)
