"""Tests for PubMed module -- uses fixture XML, no network calls."""

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from engram_r.pubmed import (
    PubMedArticle,
    _parse_article,
    fetch_articles,
    search_pubmed,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseArticle:
    """Test XML parsing with fixture data."""

    @pytest.fixture
    def article_elem(self):
        tree = ET.parse(FIXTURES / "sample_pubmed_response.xml")
        root = tree.getroot()
        return root.find("PubmedArticle")

    def test_parses_pmid(self, article_elem):
        article = _parse_article(article_elem)
        assert article.pmid == "12345678"

    def test_parses_title(self, article_elem):
        article = _parse_article(article_elem)
        assert "GFAP" in article.title

    def test_parses_authors(self, article_elem):
        article = _parse_article(article_elem)
        assert len(article.authors) == 2
        assert "Benedet A" in article.authors

    def test_parses_journal(self, article_elem):
        article = _parse_article(article_elem)
        assert article.journal == "Nature Medicine"

    def test_parses_year(self, article_elem):
        article = _parse_article(article_elem)
        assert article.year == "2021"

    def test_parses_abstract(self, article_elem):
        article = _parse_article(article_elem)
        assert "GFAP is a promising biomarker" in article.abstract
        assert "**BACKGROUND**" in article.abstract

    def test_parses_doi(self, article_elem):
        article = _parse_article(article_elem)
        assert article.doi == "10.1038/s41591-021-01234-5"


class TestSearchPubmed:
    """Test search with mocked HTTP."""

    @patch("engram_r.pubmed._fetch_xml")
    def test_returns_pmids(self, mock_fetch):
        xml_str = """<eSearchResult>
            <IdList>
                <Id>111</Id>
                <Id>222</Id>
            </IdList>
        </eSearchResult>"""
        mock_fetch.return_value = ET.fromstring(xml_str)
        result = search_pubmed("GFAP alzheimer", max_results=5)
        assert result == ["111", "222"]

    @patch("engram_r.pubmed._fetch_xml")
    def test_empty_results(self, mock_fetch):
        xml_str = "<eSearchResult><IdList></IdList></eSearchResult>"
        mock_fetch.return_value = ET.fromstring(xml_str)
        result = search_pubmed("nonexistent query xyz")
        assert result == []


class TestFetchArticles:
    def test_empty_pmids(self):
        assert fetch_articles([]) == []

    @patch("engram_r.pubmed._fetch_xml")
    def test_fetches_and_parses(self, mock_fetch):
        tree = ET.parse(FIXTURES / "sample_pubmed_response.xml")
        mock_fetch.return_value = tree.getroot()
        articles = fetch_articles(["12345678"])
        assert len(articles) == 1
        assert articles[0].pmid == "12345678"
