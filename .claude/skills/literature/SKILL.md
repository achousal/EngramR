---
name: literature
description: Search PubMed, arXiv, Semantic Scholar, and OpenAlex, create structured literature notes
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - Write
---

# /literature -- Literature Search and Summarize

Search PubMed, arXiv, Semantic Scholar, and OpenAlex, create structured literature notes in the Obsidian vault.

## Vault paths
- Literature notes: `_research/literature/` in vault root
- Template: `_code/templates/literature.md`
- Index: `_research/literature/_index.md`
- Vault root: repository root (detected automatically)

## Code location
- `_code/src/engram_r/search_interface.py` -- unified search interface for configured backends
- `_code/src/engram_r/pubmed.py` -- PubMed search via NCBI EUTILS
- `_code/src/engram_r/arxiv.py` -- arXiv Atom API search
- `_code/src/engram_r/semantic_scholar.py` -- Semantic Scholar Graph API search
- `_code/src/engram_r/openalex.py` -- OpenAlex REST API search
- `_code/src/engram_r/note_builder.py` -- `build_literature_note()`
- `_code/src/engram_r/obsidian_client.py` -- Obsidian REST API

## Workflow
1. Read `ops/config.yaml` `literature:` section via `resolve_literature_sources()` from `search_interface.py`. This returns the enabled source list and default source.
2. Present available sources to the user: sources from `resolve_literature_sources()` plus **all**. Default is `literature.default` from config. Ask for search query and source.
3. Search: always call `search_all_sources()` from `search_interface.py`.
   - **Single source**: `search_all_sources(query, sources=[chosen_source], config_path="ops/config.yaml")`
   - **all**: `search_all_sources(query, config_path="ops/config.yaml")` (uses all enabled sources from config)
   Both paths deduplicate by DOI, apply enrichment if configured, and sort by citation count descending.
4. Display results in a table with columns: **#**, **Title**, **Authors**, **Year**, **Source**, **Journal**, **DOI/ID**, **Citations**. The **Source** column shows the backend name (e.g. PubMed, Semantic Scholar). Citations shows the count or "--" when unavailable.
5. Ask the user which papers to save as notes.
6. For each selected paper, build a literature note using `build_literature_note()`, passing `source_type=result.source_type` to tag the note with the backend name.
7. Save to `_research/literature/{year}-{first_author_last_name}-{slug}.md` where slug is a short title slug.
8. Update `_research/literature/_index.md` with a link to the new note under "Recent Additions". **If `_index.md` does not exist, create it first** with frontmatter (`description: "Index of structured literature notes"`, `type: moc`, `created: {today}`), a `# Literature Index` heading, `## Recent Additions`, and `## By Topic` sections.
9. Present the saved note paths to the user.

## Note structure
Each literature note has YAML frontmatter with: type, title, doi, authors, year, journal, tags, status (unread/reading/read/cited), created date.

Sections: Abstract, Key Points, Methods Notes, Relevance, Citations.

## Rules
- Never call plt.show() or display interactive plots.
- Always use the obsidian_client for vault writes when the REST API is available; fall back to direct file writes otherwise.
- Include DOI or arXiv link in the frontmatter.
- If PubMed returns structured abstracts (labeled sections), preserve the structure.

## Pipeline Chaining

After saving literature notes and updating `_index.md`, chain to the arscontexta pipeline so literature content feeds into the knowledge graph.

**For each saved literature note:**

1. Read `ops/config.yaml` for `processing.chaining` mode.
2. Based on chaining mode:

| Mode | Action |
|------|--------|
| `manual` | Print `Next: /reduce [literature-note-path]` for each saved note |
| `suggested` (default) | Print `Next: /reduce [path]` AND create a queue entry in `ops/queue/queue.json` with `type: "extract"`, `source` pointing to the literature note path, `status: "pending"` |
| `automatic` | Print `Next: /reduce [path]` (automatic execution not yet implemented) |

**Queue entry format** (for `suggested` mode):
```json
{
  "id": "extract-{literature-note-basename}",
  "type": "extract",
  "status": "pending",
  "source": "_research/literature/{filename}.md",
  "created": "[ISO timestamp]",
  "current_phase": "reduce",
  "completed_phases": []
}
```

**Output after all notes saved:**
```
Pipeline chaining:
- _research/literature/{note1}.md -> Next: /reduce _research/literature/{note1}.md
- _research/literature/{note2}.md -> Next: /reduce _research/literature/{note2}.md
```

## Skill Graph
Invoked by: /research, user (standalone)
Invokes: /reduce (suggested chaining)
Reads: (PubMed, arXiv, Semantic Scholar, OpenAlex via API)
Writes: _research/literature/, _research/literature/_index.md, ops/queue/queue.json (chaining entries)

## Rationale
Empirical evidence gathering -- systematic search for published findings. Grounds hypotheses in existing knowledge and prevents duplication of known results.
