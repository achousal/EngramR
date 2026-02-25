---
description: The vault's self-knowledge -- derivation rationale, configuration state, and operational evolution history
type: moc
---

# methodology

This folder records what the system knows about its own operation -- why it was configured this way, what the current state is, and how it has evolved. Meta-skills (/rethink, /architect) read from and write to this folder. /remember captures operational corrections here.

## Derivation Rationale
- [[derivation-rationale]] -- Why each configuration dimension was set the way it was

## Process Patterns
- [[parallel-workflow-integrity]] -- Guardrails for parallel agent workflows: reduce fans out, reflect fans in
- [[symlinked-repos-require-wiki-link-bridges]] -- Symlinked project repos need explicit wiki-link bridges from project notes to internal docs; otherwise internal .md files are graph orphans

## Processing
- [[normalize-unicode-in-queue-ids-and-filenames]] -- Queue IDs and filenames from non-ASCII sources must use NFC-normalized UTF-8, not JSON-escaped sequences; use json.dump(ensure_ascii=False) and unicodedata.normalize("NFC", ...)

## Behavior
- [[use-git-history-as-primary-session-mining-signal]] -- Session .md stubs are always empty in this vault; git log and queue state are the actual signal sources for /remember --mine-sessions
- [[daemon-requires-consecutive-skip-idle-fallback]] -- When all tasks are marked done, the daemon must escalate to 30-minute idle cooldown rather than re-evaluating every 2 minutes indefinitely

## Quality
- [[commit-message-strings-in-yaml-source-fields-require-quoting]] -- Conventional commit type prefixes (feat:, fix:, docs:) contain colons; always double-quote source and session_source values when writing raw markdown frontmatter

## Configuration State
(Populated by /rethink, /architect)

## Evolution History
(Populated by /rethink, /architect, /reseed)

## How to Use This Folder

Browse notes: `ls ops/methodology/`
Query by category: `rg '^category:' ops/methodology/`
Find active directives: `rg '^status: active' ops/methodology/`
Ask the research graph: `/arscontexta:ask [question about your system]`

Meta-skills (/rethink, /architect) read from and write to this folder.
/remember captures operational corrections here.
