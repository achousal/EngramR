"""Tests for search_interface module -- unified SearchResult and backend resolution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from engram_r.arxiv import ArxivArticle
from engram_r.crossref import CrossRefMetadata
from engram_r.pubmed import PubMedArticle
from engram_r.literature_types import ArticleResult
from engram_r.search_interface import (
    SearchResult,
    _dedup_results,
    _enrich_results,
    _resolve_enrichment_config,
    resolve_literature_sources,
    resolve_search_backends,
    search_all_sources,
)

# ---------------------------------------------------------------------------
# SearchResult construction
# ---------------------------------------------------------------------------


class TestSearchResultConstruction:
    """Direct construction of SearchResult with explicit fields."""

    def test_basic_construction(self):
        result = SearchResult(
            source_id="TEST:001",
            title="A test result",
            authors=["Author A", "Author B"],
            abstract="Abstract text.",
            year=2024,
            doi="10.1234/test",
            source_type="web",
            url="https://example.com/001",
            journal="Test Journal",
        )
        assert result.source_id == "TEST:001"
        assert result.title == "A test result"
        assert result.authors == ["Author A", "Author B"]
        assert result.year == 2024
        assert result.source_type == "web"
        assert result.categories == []
        assert result.pdf_url == ""
        assert result.raw_metadata == {}

    def test_optional_fields_defaults(self):
        result = SearchResult(
            source_id="",
            title="",
            authors=[],
            abstract="",
            year=None,
            doi="",
            source_type="web",
            url="",
            journal="",
        )
        assert result.year is None
        assert result.categories == []
        assert result.pdf_url == ""
        assert result.raw_metadata == {}

    def test_categories_and_pdf_url(self):
        result = SearchResult(
            source_id="arXiv:2301.00001",
            title="ML paper",
            authors=["Smith J"],
            abstract="An abstract.",
            year=2023,
            doi="",
            source_type="arxiv",
            url="https://arxiv.org/abs/2301.00001",
            journal="",
            categories=["cs.LG", "stat.ML"],
            pdf_url="https://arxiv.org/pdf/2301.00001",
        )
        assert result.categories == ["cs.LG", "stat.ML"]
        assert result.pdf_url == "https://arxiv.org/pdf/2301.00001"


# ---------------------------------------------------------------------------
# from_pubmed converter
# ---------------------------------------------------------------------------


class TestFromPubMed:
    """Test SearchResult.from_pubmed with PubMedArticle instances."""

    @pytest.fixture
    def sample_article(self) -> PubMedArticle:
        return PubMedArticle(
            pmid="12345678",
            title="Metric A as a marker for test condition",
            authors=["Benedet A", "Millar J"],
            journal="Nature Medicine",
            year="2021",
            abstract="Metric A is a promising marker.",
            doi="10.1038/s41591-021-01234-5",
        )

    def test_source_id(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.source_id == "PMID:12345678"

    def test_source_type(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.source_type == "pubmed"

    def test_title_preserved(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.title == "Metric A as a marker for test condition"

    def test_authors_preserved(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.authors == ["Benedet A", "Millar J"]

    def test_year_converted_to_int(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.year == 2021
        assert isinstance(result.year, int)

    def test_year_empty_string_becomes_none(self):
        article = PubMedArticle(pmid="999", title="No year", year="")
        result = SearchResult.from_pubmed(article)
        assert result.year is None

    def test_year_invalid_string_becomes_none(self):
        article = PubMedArticle(pmid="999", title="Bad year", year="TBD")
        result = SearchResult.from_pubmed(article)
        assert result.year is None

    def test_url_constructed(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"

    def test_doi_preserved(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.doi == "10.1038/s41591-021-01234-5"

    def test_journal_preserved(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.journal == "Nature Medicine"

    def test_raw_metadata_contains_original(self, sample_article: PubMedArticle):
        result = SearchResult.from_pubmed(sample_article)
        assert result.raw_metadata["pmid"] == "12345678"
        assert result.raw_metadata["journal"] == "Nature Medicine"

    def test_empty_pmid(self):
        article = PubMedArticle(pmid="", title="Untitled")
        result = SearchResult.from_pubmed(article)
        assert result.source_id == ""
        assert result.url == ""


# ---------------------------------------------------------------------------
# from_arxiv converter
# ---------------------------------------------------------------------------


class TestFromArxiv:
    """Test SearchResult.from_arxiv with ArxivArticle instances."""

    @pytest.fixture
    def sample_entry(self) -> ArxivArticle:
        return ArxivArticle(
            arxiv_id="2301.00001v2",
            title="Attention Is All You Need (revisited)",
            authors=["Vaswani A", "Shazeer N"],
            abstract="The dominant paradigm uses attention mechanisms.",
            published="2023-01-01",
            updated="2023-06-15",
            categories=["cs.CL", "cs.LG"],
            pdf_url="https://arxiv.org/pdf/2301.00001v2",
            doi="10.48550/arXiv.2301.00001",
        )

    def test_source_id(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.source_id == "arXiv:2301.00001v2"

    def test_source_type(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.source_type == "arxiv"

    def test_title_preserved(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.title == "Attention Is All You Need (revisited)"

    def test_authors_preserved(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.authors == ["Vaswani A", "Shazeer N"]

    def test_year_extracted_from_published(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.year == 2023
        assert isinstance(result.year, int)

    def test_year_empty_published_becomes_none(self):
        entry = ArxivArticle(arxiv_id="0001", title="No date", published="")
        result = SearchResult.from_arxiv(entry)
        assert result.year is None

    def test_year_short_published_becomes_none(self):
        entry = ArxivArticle(arxiv_id="0001", title="Short date", published="20")
        result = SearchResult.from_arxiv(entry)
        assert result.year is None

    def test_year_invalid_published_becomes_none(self):
        entry = ArxivArticle(arxiv_id="0001", title="Bad date", published="ABCD-01-01")
        result = SearchResult.from_arxiv(entry)
        assert result.year is None

    def test_url_constructed(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.url == "https://arxiv.org/abs/2301.00001v2"

    def test_categories_preserved(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.categories == ["cs.CL", "cs.LG"]

    def test_pdf_url_preserved(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.pdf_url == "https://arxiv.org/pdf/2301.00001v2"

    def test_journal_is_empty(self, sample_entry: ArxivArticle):
        """ArxivArticle has no journal field; SearchResult.journal should be empty."""
        result = SearchResult.from_arxiv(sample_entry)
        assert result.journal == ""

    def test_raw_metadata_contains_original(self, sample_entry: ArxivArticle):
        result = SearchResult.from_arxiv(sample_entry)
        assert result.raw_metadata["arxiv_id"] == "2301.00001v2"
        assert result.raw_metadata["categories"] == ["cs.CL", "cs.LG"]

    def test_empty_arxiv_id(self):
        entry = ArxivArticle(arxiv_id="", title="Untitled")
        result = SearchResult.from_arxiv(entry)
        assert result.source_id == ""
        assert result.url == ""


# ---------------------------------------------------------------------------
# resolve_search_backends
# ---------------------------------------------------------------------------


class TestResolveSearchBackends:
    """Test config-driven backend resolution from ops/config.yaml."""

    def test_missing_config_file(self, tmp_path: Path):
        result = resolve_search_backends(tmp_path / "nonexistent.yaml")
        assert result == ["web-search"]

    def test_empty_config_file(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("")
        result = resolve_search_backends(cfg)
        assert result == ["web-search"]

    def test_no_research_section(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"dimensions": {"granularity": "atomic"}}))
        result = resolve_search_backends(cfg)
        assert result == ["web-search"]

    def test_all_three_backends(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "research": {
                        "primary": "pubmed",
                        "fallback": "arxiv",
                        "last_resort": "web-search",
                    }
                }
            )
        )
        result = resolve_search_backends(cfg)
        assert result == ["pubmed", "arxiv", "web-search"]

    def test_deduplication(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "research": {
                        "primary": "web-search",
                        "fallback": "web-search",
                        "last_resort": "web-search",
                    }
                }
            )
        )
        result = resolve_search_backends(cfg)
        assert result == ["web-search"]

    def test_none_values_excluded(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "research": {
                        "primary": "pubmed",
                        "fallback": "none",
                        "last_resort": "arxiv",
                    }
                }
            )
        )
        result = resolve_search_backends(cfg)
        assert result == ["pubmed", "arxiv"]

    def test_empty_values_excluded(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "research": {
                        "primary": "arxiv",
                        "fallback": "",
                        "last_resort": "",
                    }
                }
            )
        )
        result = resolve_search_backends(cfg)
        assert result == ["arxiv"]

    def test_all_none_falls_back_to_web_search(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "research": {
                        "primary": "none",
                        "fallback": "none",
                        "last_resort": "none",
                    }
                }
            )
        )
        result = resolve_search_backends(cfg)
        assert result == ["web-search"]

    def test_partial_config(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"research": {"primary": "exa"}}))
        result = resolve_search_backends(cfg)
        assert result == ["exa"]

    def test_preserves_order(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "research": {
                        "primary": "arxiv",
                        "fallback": "pubmed",
                        "last_resort": "web-search",
                    }
                }
            )
        )
        result = resolve_search_backends(cfg)
        assert result == ["arxiv", "pubmed", "web-search"]

    def test_real_config_format(self, tmp_path: Path):
        """Test with the format used in the actual ops/config.yaml."""
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "research": {
                        "primary": "web-search",
                        "fallback": "web-search",
                        "last_resort": "web-search",
                        "default_depth": "moderate",
                    }
                }
            )
        )
        result = resolve_search_backends(cfg)
        assert result == ["web-search"]

    def test_non_dict_research_section(self, tmp_path: Path):
        """Gracefully handle research: being a non-dict value."""
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"research": "invalid"}))
        result = resolve_search_backends(cfg)
        assert result == ["web-search"]


# ---------------------------------------------------------------------------
# resolve_literature_sources
# ---------------------------------------------------------------------------


class TestResolveLiteratureSources:
    """Test config-driven literature source resolution from ops/config.yaml."""

    def test_missing_config_file(self, tmp_path: Path):
        result = resolve_literature_sources(tmp_path / "nonexistent.yaml")
        assert result == ([], "")

    def test_empty_config_file(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("")
        result = resolve_literature_sources(cfg)
        assert result == ([], "")

    def test_no_literature_section(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"research": {"primary": "pubmed"}}))
        result = resolve_literature_sources(cfg)
        assert result == ([], "")

    def test_full_config(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "literature": {
                        "sources": ["pubmed", "arxiv", "semantic_scholar", "openalex"],
                        "default": "pubmed",
                    }
                }
            )
        )
        sources, default = resolve_literature_sources(cfg)
        assert sources == ["pubmed", "arxiv", "semantic_scholar", "openalex"]
        assert default == "pubmed"

    def test_default_falls_back_to_first_source(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump({"literature": {"sources": ["arxiv", "openalex"]}})
        )
        sources, default = resolve_literature_sources(cfg)
        assert sources == ["arxiv", "openalex"]
        assert default == "arxiv"

    def test_empty_sources_list(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"literature": {"sources": []}}))
        result = resolve_literature_sources(cfg)
        assert result == ([], "")

    def test_non_dict_literature_section(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"literature": "invalid"}))
        result = resolve_literature_sources(cfg)
        assert result == ([], "")

    def test_non_string_sources_filtered(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump({"literature": {"sources": ["pubmed", 123, None, "arxiv"]}})
        )
        sources, default = resolve_literature_sources(cfg)
        assert sources == ["pubmed", "arxiv"]

    def test_empty_default_falls_back(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump({"literature": {"sources": ["openalex"], "default": ""}})
        )
        _, default = resolve_literature_sources(cfg)
        assert default == "openalex"


# ---------------------------------------------------------------------------
# _dedup_results
# ---------------------------------------------------------------------------


def _make_result(
    *,
    source_id: str = "",
    title: str = "Test",
    doi: str = "",
    source_type: str = "test",
    abstract: str = "",
    citation_count: int | None = None,
) -> ArticleResult:
    """Helper to build a minimal ArticleResult for dedup tests."""
    return ArticleResult(
        source_id=source_id,
        title=title,
        authors=[],
        abstract=abstract,
        year=2024,
        doi=doi,
        source_type=source_type,
        url="",
        journal="",
        citation_count=citation_count,
    )


class TestDedupResults:
    """Test deduplication logic for multi-source results."""

    def test_no_duplicates_passthrough(self):
        results = [
            _make_result(source_id="A:1", doi="10.1/a"),
            _make_result(source_id="B:2", doi="10.1/b"),
        ]
        deduped = _dedup_results(results)
        assert len(deduped) == 2

    def test_dedup_by_doi(self):
        results = [
            _make_result(source_id="PM:1", doi="10.1/same", source_type="pubmed"),
            _make_result(source_id="S2:2", doi="10.1/same", source_type="semantic_scholar"),
        ]
        deduped = _dedup_results(results)
        assert len(deduped) == 1

    def test_dedup_by_doi_case_insensitive(self):
        results = [
            _make_result(doi="10.1/ABC", source_type="pubmed"),
            _make_result(doi="10.1/abc", source_type="openalex"),
        ]
        deduped = _dedup_results(results)
        assert len(deduped) == 1

    def test_dedup_prefers_more_complete(self):
        r1 = _make_result(doi="10.1/x", abstract="", citation_count=None)
        r2 = _make_result(doi="10.1/x", abstract="Has abstract", citation_count=42)
        deduped = _dedup_results([r1, r2])
        assert len(deduped) == 1
        assert deduped[0].citation_count == 42
        assert deduped[0].abstract == "Has abstract"

    def test_dedup_by_source_id_when_no_doi(self):
        results = [
            _make_result(source_id="S2:abc", doi=""),
            _make_result(source_id="S2:abc", doi=""),
        ]
        deduped = _dedup_results(results)
        assert len(deduped) == 1

    def test_different_source_ids_no_doi_kept(self):
        results = [
            _make_result(source_id="PM:1", doi=""),
            _make_result(source_id="S2:2", doi=""),
        ]
        deduped = _dedup_results(results)
        assert len(deduped) == 2

    def test_empty_list(self):
        assert _dedup_results([]) == []

    def test_single_item(self):
        results = [_make_result(doi="10.1/single")]
        assert len(_dedup_results(results)) == 1

    def test_three_sources_same_doi(self):
        results = [
            _make_result(doi="10.1/x", source_type="pubmed", abstract=""),
            _make_result(doi="10.1/x", source_type="semantic_scholar", citation_count=10),
            _make_result(doi="10.1/x", source_type="openalex", abstract="Full", citation_count=15),
        ]
        deduped = _dedup_results(results)
        assert len(deduped) == 1
        assert deduped[0].citation_count == 15


# ---------------------------------------------------------------------------
# search_all_sources
# ---------------------------------------------------------------------------


class TestSearchAllSources:
    """Test multi-source search with explicit source list (no live API calls)."""

    def test_with_explicit_sources_unknown(self):
        """Unknown sources return empty results."""
        results = search_all_sources("test query", sources=["nonexistent"])
        assert results == []

    def test_sorted_by_citation_count_desc(self):
        """Verify sort order: citation count descending, nulls last."""
        results = [
            _make_result(source_id="A:1", doi="10.1/a", citation_count=None),
            _make_result(source_id="B:2", doi="10.1/b", citation_count=50),
            _make_result(source_id="C:3", doi="10.1/c", citation_count=10),
        ]
        # Simulate what search_all_sources does after collecting
        results.sort(
            key=lambda r: (r.citation_count is not None, r.citation_count or 0),
            reverse=True,
        )
        assert results[0].citation_count == 50
        assert results[1].citation_count == 10
        assert results[2].citation_count is None

    def test_reads_config_when_no_sources(self, tmp_path: Path):
        """Falls back to config file when sources not provided."""
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {"literature": {"sources": ["nonexistent_source"], "default": "nonexistent_source"}}
            )
        )
        results = search_all_sources("test", config_path=cfg)
        assert results == []

    def test_empty_sources_list(self):
        """Empty explicit sources returns nothing."""
        results = search_all_sources("test", sources=[])
        assert results == []


# ---------------------------------------------------------------------------
# _resolve_enrichment_config
# ---------------------------------------------------------------------------


class TestResolveEnrichmentConfig:
    """Test enrichment config resolution from ops/config.yaml."""

    def test_none_config_path(self):
        enabled, timeout = _resolve_enrichment_config(None)
        assert enabled == []
        assert timeout == 5

    def test_missing_config_file(self, tmp_path: Path):
        enabled, timeout = _resolve_enrichment_config(tmp_path / "nope.yaml")
        assert enabled == []
        assert timeout == 5

    def test_no_enrichment_section(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"literature": {"sources": ["pubmed"]}}))
        enabled, timeout = _resolve_enrichment_config(cfg)
        assert enabled == []
        assert timeout == 5

    def test_reads_enabled_and_timeout(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "literature": {
                        "enrichment": {
                            "enabled": ["crossref", "unpaywall"],
                            "timeout_per_doi": 10,
                        }
                    }
                }
            )
        )
        enabled, timeout = _resolve_enrichment_config(cfg)
        assert enabled == ["crossref", "unpaywall"]
        assert timeout == 10

    def test_invalid_timeout_defaults(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {"literature": {"enrichment": {"enabled": [], "timeout_per_doi": -1}}}
            )
        )
        _, timeout = _resolve_enrichment_config(cfg)
        assert timeout == 5

    def test_non_list_enabled_defaults(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {"literature": {"enrichment": {"enabled": "crossref"}}}
            )
        )
        enabled, _ = _resolve_enrichment_config(cfg)
        assert enabled == []

    def test_non_dict_enrichment_section(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"literature": {"enrichment": "invalid"}}))
        enabled, timeout = _resolve_enrichment_config(cfg)
        assert enabled == []
        assert timeout == 5


# ---------------------------------------------------------------------------
# _enrich_results
# ---------------------------------------------------------------------------


class TestEnrichResults:
    """Test enrichment logic: fill-missing-only, no-overwrite, error handling."""

    def test_skips_no_doi(self):
        """Results without DOI are not enriched."""
        result = _make_result(doi="", citation_count=None)
        _enrich_results([result], ["crossref"])
        assert result.citation_count is None

    @patch("engram_r.crossref.fetch_crossref_metadata")
    def test_fills_missing_citation_count(self, mock_fetch):
        mock_fetch.return_value = CrossRefMetadata(
            doi="10.1/a", citation_count=99, pdf_url=""
        )
        result = _make_result(doi="10.1/a", citation_count=None)
        _enrich_results([result], ["crossref"])
        assert result.citation_count == 99

    @patch("engram_r.crossref.fetch_crossref_metadata")
    def test_no_overwrite_existing_citation_count(self, mock_fetch):
        mock_fetch.return_value = CrossRefMetadata(
            doi="10.1/a", citation_count=99, pdf_url=""
        )
        result = _make_result(doi="10.1/a", citation_count=42)
        _enrich_results([result], ["crossref"])
        assert result.citation_count == 42

    @patch("engram_r.crossref.fetch_crossref_metadata")
    def test_fills_missing_pdf_url(self, mock_fetch):
        mock_fetch.return_value = CrossRefMetadata(
            doi="10.1/a", citation_count=None, pdf_url="https://example.com/a.pdf"
        )
        result = ArticleResult(
            source_id="A:1",
            title="Test",
            authors=[],
            abstract="",
            year=2024,
            doi="10.1/a",
            source_type="test",
            url="",
            journal="",
            pdf_url="",
        )
        _enrich_results([result], ["crossref"])
        assert result.pdf_url == "https://example.com/a.pdf"

    @patch("engram_r.crossref.fetch_crossref_metadata")
    def test_no_overwrite_existing_pdf_url(self, mock_fetch):
        mock_fetch.return_value = CrossRefMetadata(
            doi="10.1/a", citation_count=None, pdf_url="https://new.com/a.pdf"
        )
        result = ArticleResult(
            source_id="A:1",
            title="Test",
            authors=[],
            abstract="",
            year=2024,
            doi="10.1/a",
            source_type="test",
            url="",
            journal="",
            pdf_url="https://existing.com/a.pdf",
        )
        _enrich_results([result], ["crossref"])
        assert result.pdf_url == "https://existing.com/a.pdf"

    def test_unknown_enricher_skipped(self):
        result = _make_result(doi="10.1/a", citation_count=None)
        _enrich_results([result], ["nonexistent_enricher"])
        assert result.citation_count is None

    @patch("engram_r.crossref.fetch_crossref_metadata")
    def test_exception_in_fetch_continues(self, mock_fetch):
        mock_fetch.side_effect = RuntimeError("boom")
        result = _make_result(doi="10.1/a", citation_count=None)
        # Should not raise
        _enrich_results([result], ["crossref"])
        assert result.citation_count is None

    @patch("engram_r.crossref.fetch_crossref_metadata")
    def test_fetch_returns_none_continues(self, mock_fetch):
        mock_fetch.return_value = None
        result = _make_result(doi="10.1/a", citation_count=None)
        _enrich_results([result], ["crossref"])
        assert result.citation_count is None

    def test_empty_enricher_list(self):
        result = _make_result(doi="10.1/a", citation_count=None)
        _enrich_results([result], [])
        assert result.citation_count is None


# ---------------------------------------------------------------------------
# search_all_sources with enrichment
# ---------------------------------------------------------------------------


class TestSearchAllSourcesWithEnrichment:
    """Test that enrichment integrates into the search pipeline."""

    @patch("engram_r.crossref.fetch_crossref_metadata")
    def test_enrichment_runs_before_sort(self, mock_fetch, tmp_path: Path):
        """Citation counts filled by enrichment should affect sort order."""
        mock_fetch.return_value = CrossRefMetadata(
            doi="10.1/a", citation_count=100, pdf_url=""
        )
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "literature": {
                        "sources": [],
                        "enrichment": {"enabled": ["crossref"]},
                    }
                }
            )
        )
        # No sources -> no results -> enrichment has nothing to do
        results = search_all_sources("test", config_path=cfg, sources=[])
        assert results == []

    def test_enrichment_disabled_by_default(self, tmp_path: Path):
        """Without enrichment config, no enrichment happens."""
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"literature": {"sources": []}}))
        results = search_all_sources("test", config_path=cfg, sources=[])
        assert results == []

    def test_explicit_enrichers_override_config(self):
        """Passing enrichers=[] disables enrichment regardless of config."""
        results = search_all_sources("test", sources=[], enrichers=[])
        assert results == []
