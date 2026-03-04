# /enrich-stubs -- DOI Stub Enrichment

Fetch abstracts and metadata for inbox DOI stubs created during lab onboarding. Stubs contain metadata only (title, authors, journal, DOI URL) -- this skill fills in abstracts from Semantic Scholar/PubMed plus CrossRef/Unpaywall metadata so /reduce can extract meaningful claims.

## Trigger

- `/enrich-stubs` -- enrich all DOI stubs in inbox/
- `/enrich-stubs [file]` -- enrich a single inbox file
- `/enrich-stubs --all` -- same as bare command (all stubs)

## Behavior

### Step 1: Scan

Scan `inbox/` for DOI stubs using `engram_r.stub_enricher.scan_inbox_stubs()`.

A file is a DOI stub if:
- `source_type: "import"` in frontmatter
- `source_url` contains a DOI
- No `content_depth` field set (not yet enriched)
- No `## Abstract` section with content

If a single file argument is provided, parse that file only with `parse_inbox_stub()`.

Report: "Found N DOI stubs to enrich."

If none found: "No DOI stubs found in inbox/. All files either already enriched or not import-type." and stop.

### Step 2: Enrich

For each stub, call `engram_r.stub_enricher.enrich_single_doi()`:

1. **Abstract**: Semantic Scholar DOI endpoint -> PubMed `fetch_abstract_by_doi` (fallback)
2. **Metadata**: CrossRef `fetch_crossref_metadata` (citation count, PDF URL)
3. **OA status**: Unpaywall `fetch_unpaywall_metadata` (requires `LITERATURE_ENRICHMENT_EMAIL`)

### Step 3: Apply

Call `engram_r.stub_enricher.apply_enrichment_to_stub()` for each result:
- Adds `content_depth: abstract` (or `stub` if no abstract found) to frontmatter
- Adds `citation_count`, `is_oa`, `pdf_url` to frontmatter when available
- Inserts `## Abstract` section with fetched text before `## Notes`
- Preserves all existing frontmatter and body content

### Step 4: Report

```
Enrichment complete:
  Enriched (abstract): N
  Failed (stub only):  M -- [list DOIs with reasons]
  Already enriched:    K

Next: /seed or /pipeline --all to process enriched stubs
```

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `S2_API_KEY` | No | Semantic Scholar API key (higher rate limits) |
| `LITERATURE_ENRICHMENT_EMAIL` | For Unpaywall | Contact email required by Unpaywall TOS |

## Content Depth Field

After enrichment, each stub's frontmatter includes:

| Field | Value | Meaning |
|-------|-------|---------|
| `content_depth` | `abstract` | Abstract fetched, no full text |
| `content_depth` | `stub` | Enrichment attempted but no abstract found |

This field propagates through /seed -> /reduce to control extraction scope.

## Error Handling

- Network failures per-DOI are logged but do not stop the batch
- S2 rate limiting: 1 request per second (built into the API client)
- All errors are collected and reported in the final summary
- If all enrichments fail, suggest checking network connectivity and API keys
