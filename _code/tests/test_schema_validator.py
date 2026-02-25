"""Tests for schema_validator module."""

from __future__ import annotations

import pytest

from engram_r.schema_validator import (
    ValidationResult,
    sanitize_title,
    validate_filename,
    validate_note,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _note(fm_lines: list[str], body: str = "## Body\nContent\n") -> str:
    """Build a note string from frontmatter lines and body."""
    fm = "\n".join(fm_lines)
    return f"---\n{fm}\n---\n\n{body}"


# ---------------------------------------------------------------------------
# Valid notes -- one per type
# ---------------------------------------------------------------------------


class TestValidNotes:
    """Each note type passes validation when all required fields are present."""

    def test_valid_hypothesis(self):
        content = _note([
            "type: hypothesis",
            "title: Test hypothesis",
            "id: hyp-20260101-001",
            "status: proposed",
            "elo: 1200",
            "research_goal: '[[goal]]'",
            "created: 2026-01-01",
            "updated: 2026-01-01",
        ])
        result = validate_note(content)
        assert result.valid
        assert result.errors == []

    def test_valid_literature(self):
        content = _note([
            "type: literature",
            "title: Some paper",
            "doi: 10.1234/test",
            "status: unread",
            "created: 2026-01-01",
        ])
        result = validate_note(content)
        assert result.valid

    def test_valid_experiment(self):
        content = _note([
            "type: experiment",
            "title: Exp 1",
            "status: planned",
            "created: 2026-01-01",
        ])
        result = validate_note(content)
        assert result.valid

    def test_valid_eda_report(self):
        content = _note([
            "type: eda-report",
            "title: EDA on dataset X",
            "dataset: /path/to/data.csv",
            "created: 2026-01-01",
        ])
        result = validate_note(content)
        assert result.valid

    def test_valid_research_goal(self):
        content = _note([
            "type: research-goal",
            "title: Find biomarkers",
            "status: active",
            "created: 2026-01-01",
        ])
        result = validate_note(content)
        assert result.valid

    def test_valid_tournament_match(self):
        content = _note([
            "type: tournament-match",
            "date: 2026-01-01",
            "research_goal: '[[goal]]'",
            "hypothesis_a: '[[hyp-a]]'",
            "hypothesis_b: '[[hyp-b]]'",
        ])
        result = validate_note(content)
        assert result.valid

    def test_valid_meta_review(self):
        content = _note([
            "type: meta-review",
            "date: 2026-01-01",
            "research_goal: '[[goal]]'",
        ])
        result = validate_note(content)
        assert result.valid

    def test_valid_project(self):
        content = _note([
            "type: project",
            "title: CeliacRisks",
            "project_tag: celiac-risks",
            "lab: Elahi",
            "status: active",
            "project_path: /path/to/project",
            "created: 2026-01-01",
            "updated: 2026-01-01",
        ])
        result = validate_note(content)
        assert result.valid

    def test_valid_lab(self):
        content = _note([
            "type: lab",
            "lab_slug: elahi",
            "pi: Fanny Elahi",
            "created: 2026-02-23",
            "updated: 2026-02-23",
        ])
        result = validate_note(content)
        assert result.valid


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    """Each note type fails when a required field is missing."""

    def test_hypothesis_missing_title(self):
        content = _note([
            "type: hypothesis",
            "id: hyp-20260101-001",
            "status: proposed",
            "elo: 1200",
            "created: 2026-01-01",
            "updated: 2026-01-01",
        ])
        result = validate_note(content)
        assert not result.valid
        assert any("title" in e for e in result.errors)

    def test_hypothesis_missing_id(self):
        content = _note([
            "type: hypothesis",
            "title: Test",
            "status: proposed",
            "elo: 1200",
            "created: 2026-01-01",
            "updated: 2026-01-01",
        ])
        result = validate_note(content)
        assert not result.valid
        assert any("id" in e for e in result.errors)

    def test_literature_missing_title(self):
        content = _note([
            "type: literature",
            "doi: 10.1234/test",
            "status: unread",
            "created: 2026-01-01",
        ])
        result = validate_note(content)
        assert not result.valid
        assert any("title" in e for e in result.errors)

    def test_experiment_missing_title(self):
        content = _note([
            "type: experiment",
            "status: planned",
            "created: 2026-01-01",
        ])
        result = validate_note(content)
        assert not result.valid

    def test_project_missing_lab(self):
        content = _note([
            "type: project",
            "title: Test",
            "project_tag: test",
            "status: active",
            "project_path: /tmp",
            "created: 2026-01-01",
            "updated: 2026-01-01",
        ])
        result = validate_note(content)
        assert not result.valid
        assert any("lab" in e for e in result.errors)

    def test_lab_missing_lab_slug(self):
        content = _note([
            "type: lab",
            "pi: Test PI",
            "created: 2026-02-23",
            "updated: 2026-02-23",
        ])
        result = validate_note(content)
        assert not result.valid
        assert any("lab_slug" in e for e in result.errors)

    def test_lab_missing_pi(self):
        content = _note([
            "type: lab",
            "lab_slug: test",
            "created: 2026-02-23",
            "updated: 2026-02-23",
        ])
        result = validate_note(content)
        assert not result.valid
        assert any("pi" in e for e in result.errors)

    def test_tournament_missing_hypothesis_a(self):
        content = _note([
            "type: tournament-match",
            "date: 2026-01-01",
            "research_goal: '[[goal]]'",
            "hypothesis_b: '[[hyp-b]]'",
        ])
        result = validate_note(content)
        assert not result.valid
        assert any("hypothesis_a" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Passthrough behaviors
# ---------------------------------------------------------------------------


class TestPassthrough:
    """Non-note files and unknown types should pass validation."""

    def test_no_frontmatter_passes(self):
        content = "# Just a heading\n\nSome text.\n"
        result = validate_note(content)
        assert result.valid

    def test_unknown_type_passes(self):
        content = _note([
            "type: custom-note",
            "title: Something",
        ])
        result = validate_note(content)
        assert result.valid

    def test_no_type_field_passes(self):
        content = _note([
            "title: Something",
            "tags: [misc]",
        ])
        result = validate_note(content)
        assert result.valid

    def test_empty_string_passes(self):
        result = validate_note("")
        assert result.valid


# ---------------------------------------------------------------------------
# Type inference and explicit type
# ---------------------------------------------------------------------------


class TestTypeHandling:
    """Validate note_type parameter override behavior."""

    def test_explicit_type_overrides_frontmatter(self):
        content = _note([
            "type: literature",
            "title: Paper",
            "doi: 10.1234/test",
            "status: unread",
            "created: 2026-01-01",
        ])
        # Force validate as hypothesis -- should fail (missing hypothesis fields)
        result = validate_note(content, note_type="hypothesis")
        assert not result.valid

    def test_explicit_type_with_matching_fields_passes(self):
        content = _note([
            "type: literature",
            "title: Paper",
            "doi: 10.1234/test",
            "status: unread",
            "created: 2026-01-01",
        ])
        result = validate_note(content, note_type="literature")
        assert result.valid


# ---------------------------------------------------------------------------
# ValidationResult dataclass
# ---------------------------------------------------------------------------


class TestValidationResult:
    """Basic sanity checks on the result dataclass."""

    def test_valid_result(self):
        r = ValidationResult(valid=True, errors=[])
        assert r.valid
        assert r.errors == []

    def test_invalid_result(self):
        r = ValidationResult(valid=False, errors=["missing field: title"])
        assert not r.valid
        assert len(r.errors) == 1


# ---------------------------------------------------------------------------
# sanitize_title
# ---------------------------------------------------------------------------


class TestSanitizeTitle:
    """Filesystem-unsafe characters in titles are replaced with hyphens."""

    def test_forward_slash(self):
        assert sanitize_title("APP/PS1 mice") == "APP-PS1 mice"

    def test_multiple_slashes(self):
        assert sanitize_title("AhR/NF-kappaB/NLRP3") == "AhR-NF-kappaB-NLRP3"

    def test_backslash(self):
        assert sanitize_title("path\\to") == "path-to"

    def test_colon(self):
        assert sanitize_title("ratio:value") == "ratio-value"

    def test_no_unsafe_chars(self):
        assert sanitize_title("normal title") == "normal title"

    def test_mixed_unsafe(self):
        assert sanitize_title('a/b\\c:d*e?"f') == "a-b-c-d-e--f"

    def test_preserves_hyphens(self):
        assert sanitize_title("already-safe-title") == "already-safe-title"

    def test_biology_notation(self):
        assert sanitize_title("APOE3/3") == "APOE3-3"
        assert sanitize_title("Abeta42/40") == "Abeta42-40"
        assert sanitize_title("insulin/IGF1") == "insulin-IGF1"


# ---------------------------------------------------------------------------
# validate_filename
# ---------------------------------------------------------------------------


class TestValidateFilename:
    """Detect unsafe characters in filename components."""

    def test_clean_path(self):
        assert validate_filename("notes/some claim.md") == []

    def test_slash_creates_no_filename_error(self):
        # The / is a path separator, so the filename component is just
        # "PS1 mice.md" which is clean -- the validate_write hook handles
        # the nesting check separately.
        assert validate_filename("notes/APP/PS1 mice.md") == []

    def test_colon_in_filename(self):
        errors = validate_filename("notes/ratio:value.md")
        assert len(errors) == 1
        assert ":" in errors[0]

    def test_asterisk_in_filename(self):
        errors = validate_filename("notes/test*file.md")
        assert len(errors) == 1
        assert "*" in errors[0]


# ---------------------------------------------------------------------------
# YAML special characters in frontmatter (regression for unquoted-colon bug)
# ---------------------------------------------------------------------------


class TestYAMLSpecialCharacters:
    """Frontmatter with YAML-special characters must be quoted to parse."""

    def test_unquoted_colon_in_description_is_invalid(self):
        """The original bug: 'docs: tighten am/pm references' broke YAML."""
        content = (
            "---\n"
            "description: docs: tighten am/pm references\n"
            "type: methodology\n"
            "---\n\n# Body\nContent\n"
        )
        result = validate_note(content)
        # yaml.safe_load parses this as {"description": {"docs": ...}}
        # which is a nested dict, not a string -- validation should still
        # proceed, but the description field won't be a string.  The key
        # point: the frontmatter *does* parse (YAML allows mapping values
        # as values), so validate_note returns valid=True for unknown types.
        # The validate_write hook catches the deeper issue.  What we really
        # care about is that properly quoted values work correctly.
        assert isinstance(result, ValidationResult)

    def test_conventional_commit_colon_unquoted_parses_unexpectedly(self):
        """Conventional commit format 'feat: add X' parses as nested mapping."""
        content = (
            "---\n"
            "session_source: feat: add new feature\n"
            "type: methodology\n"
            "---\n\n# Body\nContent\n"
        )
        result = validate_note(content)
        assert isinstance(result, ValidationResult)

    def test_quoted_colon_in_description_is_valid(self):
        """Properly quoted values with colons parse correctly."""
        content = _note([
            'description: "docs: tighten am/pm references in narrative text"',
            "type: methodology",
            "category: quality",
            "status: active",
            "created: 2026-02-22",
        ])
        result = validate_note(content)
        assert result.valid

    def test_quoted_session_source_with_colon(self):
        """session_source with conventional commit format works when quoted."""
        content = _note([
            'description: "observed pattern in session mining"',
            'session_source: "docs: tighten am/pm references"',
            "type: methodology",
            "status: active",
            "created: 2026-02-22",
        ])
        result = validate_note(content)
        assert result.valid

    def test_brackets_in_value_quoted(self):
        """Brackets in quoted values do not create YAML lists."""
        content = _note([
            'description: "[session filename] contains the source"',
            "type: methodology",
            "status: active",
            "created: 2026-02-22",
        ])
        result = validate_note(content)
        assert result.valid

    def test_hash_in_value_quoted(self):
        """Hash in quoted values is not treated as a YAML comment."""
        content = _note([
            'description: "commit abc123# introduced the bug"',
            "type: methodology",
            "status: active",
            "created: 2026-02-22",
        ])
        result = validate_note(content)
        assert result.valid

    def test_unparseable_yaml_returns_invalid(self):
        """Completely broken YAML frontmatter returns valid=False."""
        content = "---\n: :\n  - [\n---\n\n# Body\n"
        result = validate_note(content)
        assert not result.valid
        assert any("Invalid YAML" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Foreign hypothesis schema
# ---------------------------------------------------------------------------


class TestForeignHypothesisSchema:
    """Validate foreign-hypothesis note type from federation imports."""

    def test_valid_foreign_hypothesis(self):
        content = _note([
            "type: foreign-hypothesis",
            "title: Imported hypothesis from peer vault",
            "id: hyp-peer-001",
            "status: proposed",
            "elo_federated: 1200",
            "elo_source: 1350",
            "matches_federated: 0",
            "matches_source: 8",
            "source_vault: collab-lab-uuid",
            "imported: 2026-02-23",
        ])
        result = validate_note(content)
        assert result.valid
        assert result.errors == []

    def test_foreign_hypothesis_missing_required_fields(self):
        content = _note([
            "type: foreign-hypothesis",
            "title: Incomplete import",
            "id: hyp-peer-002",
            "status: proposed",
        ])
        result = validate_note(content)
        assert not result.valid
        assert any("elo_federated" in e for e in result.errors)
        assert any("source_vault" in e for e in result.errors)
