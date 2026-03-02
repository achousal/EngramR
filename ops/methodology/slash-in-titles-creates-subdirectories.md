---
description: Forward slashes in claim titles create accidental subdirectories instead of flat files -- validated guardrail in validate_write hook
category: process-pattern
status: active
created: 2026-02-23
---

# Slash in titles creates subdirectories

## Problem

Domain notation frequently uses `/` (e.g., cost/benefit, input/output, v2/3). When these appear in claim titles, the Write tool interprets `/` as a directory separator, creating nested subdirectories under notes/ instead of flat files.

Example: `notes/...cost/benefit analysis.md` becomes directory `notes/...cost/` containing `benefit analysis.md`.

## Impact

- Orphan detection reports the fragment files as orphans
- Wiki links referencing the full title resolve incorrectly
- The notes/ directory loses its flat structure invariant

## Root cause

/reduce extracts titles from source material without sanitizing filesystem-unsafe characters before writing.

## Fix (2026-02-23)

Three-layer prevention:

1. **validate_write.py hook** -- blocks writes to notes/, hypotheses/, literature/, experiments/ that create nesting (detects 3+ path components)
2. **sanitize_title() in schema_validator.py** -- replaces `/\:*?"<>|` with `-`, available for any code path
3. **CLAUDE.md title rules** -- explicitly lists `/` as banned, with examples showing `-` as replacement

## Convention

Use `-` instead of `/` in all claim titles: cost-benefit, input-output, v2-3, client-server, read-write.
