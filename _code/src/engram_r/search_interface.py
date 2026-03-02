"""Unified search interface for literature backends.

Provides SearchResult (backward-compatible alias for ArticleResult),
resolve_search_backends() for config-driven backend selection, and
multi-source search with deduplication via search_all_sources().

The canonical type definition lives in literature_types.py. This module
re-exports it as SearchResult for backward compatibility with existing
code that imports from here.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from engram_r.literature_types import ArticleResult

logger = logging.getLogger(__name__)

_ENRICHER_REGISTRY: dict[str, tuple[str, str]] = {
    "crossref": ("engram_r.crossref", "fetch_crossref_metadata"),
    "unpaywall": ("engram_r.unpaywall", "fetch_unpaywall_metadata"),
}

# Backward-compatible alias -- existing code imports SearchResult from here.
SearchResult = ArticleResult

# Maps config source names to (module, search_function, converter) for dispatch.
_SOURCE_REGISTRY: dict[str, tuple[str, str, str]] = {
    "pubmed": ("engram_r.pubmed", "search_and_fetch", "from_pubmed"),
    "arxiv": ("engram_r.arxiv", "search_arxiv", "from_arxiv"),
    "semantic_scholar": (
        "engram_r.semantic_scholar",
        "search_semantic_scholar",
        "from_semantic_scholar",
    ),
    "openalex": ("engram_r.openalex", "search_openalex", "from_openalex"),
}


def resolve_search_backends(
    config_path: Path | str,
) -> list[str]:
    """Read configured search backends from ops/config.yaml.

    Returns ordered list: [primary, fallback, last_resort].
    Backends with value "none" or empty are excluded. Duplicates
    are removed (first occurrence wins).

    Args:
        config_path: Path to ops/config.yaml.

    Returns:
        Ordered list of backend names (e.g. ["pubmed", "arxiv", "web-search"]).
        Falls back to ["web-search"] if the config file is missing or
        no backends are configured.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        return ["web-search"]

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    research = config.get("research", {})
    if not isinstance(research, dict):
        return ["web-search"]

    backends: list[str] = []
    for key in ("primary", "fallback", "last_resort"):
        value = research.get(key, "")
        if (
            isinstance(value, str)
            and value
            and value != "none"
            and value not in backends
        ):
            backends.append(value)

    return backends if backends else ["web-search"]


def resolve_literature_sources(
    config_path: Path | str,
) -> tuple[list[str], str]:
    """Read literature sources and default from ops/config.yaml.

    Reads the ``literature:`` section which lists enabled sources
    and the default source for the /literature skill.

    Args:
        config_path: Path to ops/config.yaml.

    Returns:
        Tuple of (enabled_sources, default_source).
        Returns ``([], "")`` if the config is missing or has no
        literature section.
    """
    config_path = Path(config_path)
    fallback: tuple[list[str], str] = ([], "")

    if not config_path.exists():
        return fallback

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    lit = config.get("literature", {})
    if not isinstance(lit, dict):
        return fallback

    sources = lit.get("sources", [])
    if not isinstance(sources, list) or not sources:
        return fallback

    # Filter to strings only
    sources = [s for s in sources if isinstance(s, str) and s]
    if not sources:
        return fallback

    default = lit.get("default", sources[0])
    if not isinstance(default, str) or not default:
        default = sources[0]

    return sources, default


def _search_single_source(
    source_name: str,
    query: str,
    max_results: int,
) -> list[ArticleResult]:
    """Search a single source and convert results to ArticleResult.

    Dynamically imports the source module to avoid loading all backends
    at module import time. Returns an empty list if the source is
    unknown or the search fails.
    """
    import importlib

    registry_entry = _SOURCE_REGISTRY.get(source_name)
    if registry_entry is None:
        logger.warning("Unknown literature source: %s", source_name)
        return []

    module_path, func_name, converter_name = registry_entry
    try:
        mod = importlib.import_module(module_path)
    except ImportError:
        logger.warning("Could not import module for source: %s", source_name)
        return []

    search_fn = getattr(mod, func_name, None)
    if search_fn is None:
        logger.warning("Search function %s not found in %s", func_name, module_path)
        return []

    converter = getattr(ArticleResult, converter_name, None)
    if converter is None:
        logger.warning("Converter %s not found on ArticleResult", converter_name)
        return []

    try:
        raw_results = search_fn(query, max_results)
    except Exception:
        logger.exception("Search failed for source: %s", source_name)
        return []

    return [converter(r) for r in raw_results]


def _dedup_results(results: list[ArticleResult]) -> list[ArticleResult]:
    """Deduplicate ArticleResult list by DOI (primary) then source_id.

    When duplicates are found, keeps the result with more metadata
    (prefers: has citation_count > has abstract > first seen).
    """
    seen_dois: dict[str, int] = {}
    seen_source_ids: dict[str, int] = {}
    deduped: list[ArticleResult] = []

    def _completeness(r: ArticleResult) -> int:
        score = 0
        if r.citation_count is not None:
            score += 2
        if r.abstract:
            score += 1
        return score

    for result in results:
        # Check DOI dedup
        if result.doi:
            doi_lower = result.doi.lower()
            if doi_lower in seen_dois:
                existing_idx = seen_dois[doi_lower]
                if _completeness(result) > _completeness(deduped[existing_idx]):
                    deduped[existing_idx] = result
                continue
            seen_dois[doi_lower] = len(deduped)

        # Check source_id dedup (only if no DOI matched)
        if result.source_id:
            if result.source_id in seen_source_ids:
                existing_idx = seen_source_ids[result.source_id]
                if _completeness(result) > _completeness(deduped[existing_idx]):
                    deduped[existing_idx] = result
                continue
            seen_source_ids[result.source_id] = len(deduped)

        deduped.append(result)

    return deduped


def _resolve_enrichment_config(
    config_path: Path | str | None,
) -> tuple[list[str], int]:
    """Read enrichment settings from ops/config.yaml.

    Returns:
        Tuple of (enabled_enrichers, timeout_per_doi).
        Falls back to ([], 5) if config is missing or has no enrichment section.
    """
    fallback: tuple[list[str], int] = ([], 5)
    if config_path is None:
        return fallback

    config_path = Path(config_path)
    if not config_path.exists():
        return fallback

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    lit = config.get("literature", {})
    if not isinstance(lit, dict):
        return fallback

    enrichment = lit.get("enrichment", {})
    if not isinstance(enrichment, dict):
        return fallback

    enabled = enrichment.get("enabled", [])
    if not isinstance(enabled, list):
        enabled = []
    enabled = [e for e in enabled if isinstance(e, str) and e]

    timeout = enrichment.get("timeout_per_doi", 5)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        timeout = 5

    return enabled, int(timeout)


def _enrich_results(
    results: list[ArticleResult],
    enrichers: list[str],
    timeout: int = 5,
) -> list[ArticleResult]:
    """Enrich ArticleResult list by fetching metadata from enrichment APIs.

    For each enricher, iterates results with a DOI and fills MISSING fields
    only (never overwrites existing data). Enrichers run in the order given.

    Args:
        results: Deduplicated list of ArticleResult to enrich.
        enrichers: Ordered list of enricher names (e.g. ["crossref", "unpaywall"]).
        timeout: Per-DOI timeout in seconds.

    Returns:
        The same list, mutated in place (also returned for convenience).
    """
    import importlib

    email = os.environ.get("LITERATURE_ENRICHMENT_EMAIL", "")

    for enricher_name in enrichers:
        registry_entry = _ENRICHER_REGISTRY.get(enricher_name)
        if registry_entry is None:
            logger.warning("Unknown enricher: %s", enricher_name)
            continue

        module_path, func_name = registry_entry
        try:
            mod = importlib.import_module(module_path)
        except ImportError:
            logger.warning("Could not import enricher module: %s", module_path)
            continue

        fetch_fn = getattr(mod, func_name, None)
        if fetch_fn is None:
            logger.warning("Fetch function %s not found in %s", func_name, module_path)
            continue

        for result in results:
            if not result.doi:
                continue

            try:
                metadata = fetch_fn(result.doi, email=email, timeout=timeout)
            except Exception:
                logger.debug("Enricher %s failed for DOI %s", enricher_name, result.doi)
                continue

            if metadata is None:
                continue

            # Fill missing fields only -- never overwrite
            if result.citation_count is None and hasattr(metadata, "citation_count"):
                cc = getattr(metadata, "citation_count", None)
                if cc is not None:
                    result.citation_count = cc

            if not result.pdf_url and hasattr(metadata, "pdf_url"):
                pdf = getattr(metadata, "pdf_url", "")
                if pdf:
                    result.pdf_url = pdf

    return results


def search_all_sources(
    query: str,
    max_results_per_source: int = 5,
    config_path: Path | str | None = None,
    sources: list[str] | None = None,
    enrichers: list[str] | None = None,
) -> list[ArticleResult]:
    """Search multiple literature sources, enrich, and deduplicate results.

    Searches each enabled source sequentially, converts to ArticleResult,
    deduplicates by DOI (primary) then source_id (fallback), optionally
    enriches via CrossRef/Unpaywall, and returns sorted by citation count
    descending (nulls last).

    Args:
        query: Free-text search query.
        max_results_per_source: Max results to fetch from each source.
        config_path: Path to ops/config.yaml for source list and
            enrichment config. Ignored for sources if ``sources`` is provided.
        sources: Explicit list of source names to search. Overrides config.
        enrichers: Explicit list of enricher names. Overrides config.
            Pass ``[]`` to disable enrichment.

    Returns:
        Deduplicated list of ArticleResult sorted by citation count.
    """
    if sources is None:
        if config_path is not None:
            enabled, _ = resolve_literature_sources(config_path)
        else:
            enabled = list(_SOURCE_REGISTRY.keys())
        sources = enabled

    all_results: list[ArticleResult] = []
    for source_name in sources:
        results = _search_single_source(source_name, query, max_results_per_source)
        all_results.extend(results)

    deduped = _dedup_results(all_results)

    # Enrichment: fill missing citation_count and pdf_url via DOI lookups
    if enrichers is None:
        enricher_list, enrich_timeout = _resolve_enrichment_config(config_path)
    else:
        enricher_list = enrichers
        _, enrich_timeout = _resolve_enrichment_config(config_path)

    if enricher_list:
        _enrich_results(deduped, enricher_list, timeout=enrich_timeout)

    # Sort by citation count descending, nulls last
    def _sort_key(r: ArticleResult) -> tuple[bool, int]:
        return (r.citation_count is not None, r.citation_count or 0)

    deduped.sort(key=_sort_key, reverse=True)

    return deduped
