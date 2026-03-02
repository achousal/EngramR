---
description: "Health reports and queue task files are operational artifacts that should be excluded from link health scanning to prevent self-referential dangling link inflation"
type: methodology
category: health-pattern
status: active
created: 2026-02-23
---

# health reports are diagnostic artifacts not graph nodes

Health reports (ops/health/) and queue task files (ops/queue/) contain wiki link syntax for readability but are not knowledge graph nodes. When the /health skill scans these directories for dangling links, it counts its own diagnostic output as graph breakage -- a self-referential loop that inflates the dangling link count without reflecting actual knowledge graph problems.

Root causes observed (2026-02-23, report-8):
- **Truncated links in queue files**: /reflect phase agents write shorthand like `[[NLRP3 inflammasome...]]` in evaluation logs. These are note-taking abbreviations, not intended graph edges.
- **Colon-in-title references in health reports**: health reports quote note titles verbatim, including colons that break wiki link resolution.
- **Transclusion syntax**: `![[path/to/file]]` in projects/ is valid Obsidian syntax but flagged by simple link resolution.

The canonical link checker (ops/scripts/dangling-links.sh) is correctly scoped to knowledge graph directories only: notes/, _research/, self/, projects/. The /health skill should either use this script as its link checker or apply equivalent directory scoping.

Fixes applied:
1. Truncated links in queue files converted to backtick code spans
2. Colon-in-title notes corrected to use hyphens
3. Stale health reports deleted (only latest kept)
4. validate-note.sh hook blocks truncated wiki links on write
