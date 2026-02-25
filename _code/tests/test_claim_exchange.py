"""Tests for claim_exchange module -- export/import for cross-vault federation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from engram_r.claim_exchange import (
    ClaimExchangeError,
    ExportedClaim,
    _safe_filename,
    _strip_wiki_links,
    export_claim,
    export_claims,
    export_to_yaml,
    import_claims,
    load_exported_claims,
)

_NOW = datetime(2026, 2, 23, 12, 0, 0, tzinfo=UTC)

_SAMPLE_NOTE = """\
---
description: "Ceramide levels increase in AD brains"
type: evidence
confidence: supported
source: "[[smith-2024-ceramides]]"
source_class: published
verified_by: human
verified_who: "Andres Chousal"
verified_date: "2026-02-25"
tags:
  - lipids
  - AD
---

Ceramide accumulation in temporal cortex is associated with
[[amyloid plaque burden]] in post-mortem tissue.

Relevant Claims:
- [[amyloid drives ceramide synthesis]] -- mechanistic basis
"""


class TestStripWikiLinks:
    """Test wiki-link to plain text conversion."""

    def test_simple_link(self) -> None:
        assert _strip_wiki_links("see [[foo bar]]") == "see foo bar"

    def test_display_text(self) -> None:
        assert _strip_wiki_links("see [[foo|Bar]]") == "see Bar"

    def test_multiple_links(self) -> None:
        text = "[[a]] and [[b|B]] plus [[c]]"
        assert _strip_wiki_links(text) == "a and B plus c"

    def test_no_links(self) -> None:
        assert _strip_wiki_links("plain text") == "plain text"

    def test_nested_brackets(self) -> None:
        assert _strip_wiki_links("[[x]]") == "x"


class TestExportClaim:
    """Test single claim export."""

    def test_basic_export(self) -> None:
        claim = export_claim(
            _SAMPLE_NOTE,
            title="ceramide levels increase in AD brains",
            source_vault="main",
            now=_NOW,
        )
        assert claim.title == "ceramide levels increase in AD brains"
        assert claim.description == "Ceramide levels increase in AD brains"
        assert claim.type == "evidence"
        assert claim.confidence == "supported"
        assert claim.source == "smith-2024-ceramides"  # wiki-link stripped
        assert claim.source_class == "published"
        assert claim.verified_by == "human"
        assert claim.verified_who == "Andres Chousal"
        assert claim.verified_date == "2026-02-25"
        assert claim.tags == ["lipids", "AD"]
        assert claim.source_vault == "main"
        assert "amyloid plaque burden" in claim.body  # link stripped
        assert "[[" not in claim.body  # no wiki-links in body

    def test_exported_timestamp(self) -> None:
        claim = export_claim(
            _SAMPLE_NOTE,
            title="test",
            source_vault="v",
            now=_NOW,
        )
        assert claim.exported == "2026-02-23T12:00:00+00:00"

    def test_minimal_note(self) -> None:
        content = "---\ndescription: minimal\n---\n\nBody text.\n"
        claim = export_claim(content, title="minimal claim", source_vault="v", now=_NOW)
        assert claim.title == "minimal claim"
        assert claim.description == "minimal"
        assert claim.type == "claim"
        assert claim.body == "Body text."

    def test_no_frontmatter_raises(self) -> None:
        with pytest.raises(ClaimExchangeError, match="frontmatter"):
            export_claim("no frontmatter here", title="x", source_vault="v")

    def test_invalid_yaml_raises(self) -> None:
        content = "---\n: :\n---\n\nbody\n"
        with pytest.raises(ClaimExchangeError):
            export_claim(content, title="x", source_vault="v")


class TestExportClaims:
    """Test bulk export from a vault directory."""

    @pytest.fixture()
    def vault(self, tmp_path: Path) -> Path:
        notes = tmp_path / "notes"
        notes.mkdir()
        # Create 3 notes
        (notes / "claim-a.md").write_text(
            '---\ndescription: "A"\ntype: claim\nconfidence: supported\n'
            "tags: [x]\n---\n\nBody A.\n"
        )
        (notes / "claim-b.md").write_text(
            '---\ndescription: "B"\ntype: evidence\nconfidence: established\n'
            "tags: [y]\n---\n\nBody B.\n"
        )
        (notes / "claim-c.md").write_text(
            '---\ndescription: "C"\ntype: claim\nconfidence: preliminary\n'
            "tags: [x, z]\n---\n\nBody C.\n"
        )
        return tmp_path

    def test_exports_all(self, vault: Path) -> None:
        claims = export_claims(vault, source_vault="test", now=_NOW)
        assert len(claims) == 3

    def test_filter_by_type(self, vault: Path) -> None:
        claims = export_claims(
            vault, source_vault="test", filter_type="evidence", now=_NOW
        )
        assert len(claims) == 1
        assert claims[0].type == "evidence"

    def test_filter_by_confidence(self, vault: Path) -> None:
        claims = export_claims(
            vault,
            source_vault="test",
            filter_confidence="supported",
            now=_NOW,
        )
        assert len(claims) == 1
        assert claims[0].confidence == "supported"

    def test_filter_by_tags(self, vault: Path) -> None:
        claims = export_claims(vault, source_vault="test", filter_tags=["x"], now=_NOW)
        assert len(claims) == 2  # claim-a and claim-c

    def test_filter_by_multiple_tags(self, vault: Path) -> None:
        claims = export_claims(
            vault, source_vault="test", filter_tags=["x", "z"], now=_NOW
        )
        assert len(claims) == 1  # only claim-c has both

    def test_missing_notes_dir(self, tmp_path: Path) -> None:
        claims = export_claims(tmp_path, source_vault="test")
        assert claims == []

    def test_skips_malformed_notes(self, vault: Path) -> None:
        (vault / "notes" / "bad.md").write_text("no frontmatter")
        claims = export_claims(vault, source_vault="test", now=_NOW)
        assert len(claims) == 3  # bad note skipped


class TestYamlRoundTrip:
    """Test YAML serialization/deserialization."""

    def test_round_trip(self) -> None:
        original = [
            ExportedClaim(
                title="test claim",
                description="desc",
                type="evidence",
                confidence="supported",
                source="Smith 2024",
                source_class="published",
                verified_by="human",
                verified_who="Andres Chousal",
                verified_date="2026-02-25",
                tags=["a", "b"],
                body="Body text here.",
                source_vault="main",
                exported="2026-02-23T12:00:00+00:00",
            )
        ]
        yaml_str = export_to_yaml(original)
        loaded = load_exported_claims(yaml_str)
        assert len(loaded) == 1
        assert loaded[0].title == original[0].title
        assert loaded[0].description == original[0].description
        assert loaded[0].type == original[0].type
        assert loaded[0].confidence == original[0].confidence
        assert loaded[0].source == original[0].source
        assert loaded[0].source_class == original[0].source_class
        assert loaded[0].verified_by == original[0].verified_by
        assert loaded[0].verified_who == original[0].verified_who
        assert loaded[0].verified_date == original[0].verified_date
        assert loaded[0].tags == original[0].tags
        assert loaded[0].body == original[0].body
        assert loaded[0].source_vault == original[0].source_vault

    def test_load_invalid_yaml(self) -> None:
        with pytest.raises(ClaimExchangeError):
            load_exported_claims(":::bad")

    def test_load_non_list(self) -> None:
        with pytest.raises(ClaimExchangeError, match="list"):
            load_exported_claims("key: value")

    def test_load_skips_non_dict_items(self) -> None:
        result = load_exported_claims("- title: ok\n- just a string\n")
        assert len(result) == 1

    def test_load_skips_items_without_title(self) -> None:
        result = load_exported_claims("- description: no title\n")
        assert len(result) == 0

    def test_empty_list(self) -> None:
        result = load_exported_claims("[]")
        assert result == []


class TestImportClaims:
    """Test importing claims into a vault."""

    @pytest.fixture()
    def vault(self, tmp_path: Path) -> Path:
        (tmp_path / "notes").mkdir()
        return tmp_path

    def _make_claim(self, title: str = "test claim") -> ExportedClaim:
        return ExportedClaim(
            title=title,
            description="A test description",
            type="claim",
            confidence="supported",
            source="Smith 2024",
            source_class="published",
            verified_by="human",
            verified_who="Andres Chousal",
            verified_date="2026-02-25",
            tags=["lipids"],
            body="Body content here.",
            source_vault="other-vault",
            exported="2026-02-23T12:00:00+00:00",
        )

    def test_creates_note_file(self, vault: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(vault, claims)
        assert len(created) == 1
        assert created[0].exists()

    def test_quarantine_flag_added(self, vault: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(vault, claims, quarantine=True)
        content = created[0].read_text(encoding="utf-8")
        assert "quarantine: true" in content

    def test_quarantine_flag_omitted(self, vault: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(vault, claims, quarantine=False)
        content = created[0].read_text(encoding="utf-8")
        assert "quarantine" not in content

    def test_source_vault_in_frontmatter(self, vault: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(vault, claims)
        content = created[0].read_text(encoding="utf-8")
        assert "source_vault: other-vault" in content

    def test_preserves_body(self, vault: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(vault, claims)
        content = created[0].read_text(encoding="utf-8")
        assert "Body content here." in content

    def test_does_not_overwrite_by_default(self, vault: Path) -> None:
        note_path = vault / "notes" / "test claim.md"
        note_path.write_text("existing content")
        claims = [self._make_claim()]
        created = import_claims(vault, claims, overwrite=False)
        assert len(created) == 0
        assert note_path.read_text() == "existing content"

    def test_overwrite_replaces(self, vault: Path) -> None:
        note_path = vault / "notes" / "test claim.md"
        note_path.write_text("existing content")
        claims = [self._make_claim()]
        created = import_claims(vault, claims, overwrite=True)
        assert len(created) == 1
        assert "Body content here." in created[0].read_text()

    def test_creates_notes_dir_if_missing(self, tmp_path: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(tmp_path, claims)
        assert len(created) == 1
        assert (tmp_path / "notes").is_dir()

    def test_multiple_claims(self, vault: Path) -> None:
        claims = [self._make_claim("claim one"), self._make_claim("claim two")]
        created = import_claims(vault, claims)
        assert len(created) == 2

    def test_frontmatter_is_valid_yaml(self, vault: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(vault, claims)
        content = created[0].read_text(encoding="utf-8")
        # Parse the frontmatter
        match = __import__("re").match(
            r"^---\s*\n(.*?)\n---\s*\n", content, __import__("re").DOTALL
        )
        assert match is not None
        fm = yaml.safe_load(match.group(1))
        assert isinstance(fm, dict)
        assert fm["type"] == "claim"
        assert fm["confidence"] == "supported"

    def test_imported_timestamp(self, vault: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(vault, claims)
        content = created[0].read_text(encoding="utf-8")
        assert "imported:" in content

    def test_provenance_fields_in_imported_note(self, vault: Path) -> None:
        claims = [self._make_claim()]
        created = import_claims(vault, claims)
        content = created[0].read_text(encoding="utf-8")
        assert "source_class: published" in content
        assert "verified_by: human" in content
        assert "verified_who: Andres Chousal" in content
        assert "verified_date: '2026-02-25'" in content or "verified_date: 2026-02-25" in content


class TestSafeFilename:
    """Test filename sanitization."""

    def test_slashes(self) -> None:
        assert "/" not in _safe_filename("a/b/c")

    def test_colons(self) -> None:
        assert ":" not in _safe_filename("a:b")

    def test_brackets(self) -> None:
        assert "[" not in _safe_filename("a[b]c")

    def test_preserves_hyphens(self) -> None:
        assert _safe_filename("a-b-c") == "a-b-c"

    def test_preserves_spaces(self) -> None:
        assert _safe_filename("hello world") == "hello world"


class TestFullRoundTrip:
    """Test complete export -> YAML -> load -> import cycle."""

    def test_round_trip_preserves_content(self, tmp_path: Path) -> None:
        # Source vault with a claim
        src = tmp_path / "src"
        (src / "notes").mkdir(parents=True)
        note_content = (
            "---\n"
            'description: "Ceramide levels rise in AD"\n'
            "type: evidence\n"
            "confidence: supported\n"
            'source: "[[smith-2024]]"\n'
            "tags:\n"
            "  - lipids\n"
            "---\n\n"
            "Ceramide is linked to [[amyloid pathology]].\n"
        )
        (src / "notes" / "ceramide-rises-in-ad.md").write_text(note_content)

        # Export
        claims = export_claims(src, source_vault="lab-a", now=_NOW)
        assert len(claims) == 1

        # Serialize + deserialize
        yaml_str = export_to_yaml(claims)
        loaded = load_exported_claims(yaml_str)
        assert len(loaded) == 1

        # Import into target vault
        dst = tmp_path / "dst"
        created = import_claims(dst, loaded)
        assert len(created) == 1

        # Verify imported content
        content = created[0].read_text(encoding="utf-8")
        assert "Ceramide levels rise in AD" in content
        assert "source_vault: lab-a" in content
        assert "quarantine: true" in content
        assert "amyloid pathology" in content  # link stripped but text preserved
        assert "[[" not in content  # no wiki-links in imported note
        assert "smith-2024" in content  # source as citation
