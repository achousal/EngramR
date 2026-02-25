---
description: Forward slashes in claim titles create accidental subdirectories instead of flat files -- validated guardrail in validate_write hook
category: process-pattern
status: active
created: 2026-02-23
---

# Slash in titles creates subdirectories

## Problem

Biology notation frequently uses `/` (APP/PS1, APOE3/3, Abeta42/40, AhR/NF-kappaB/NLRP3, insulin/IGF1). When these appear in claim titles, the Write tool interprets `/` as a directory separator, creating nested subdirectories under notes/ instead of flat files.

Example: `notes/...in APP/PS1 mice.md` becomes directory `notes/...in APP/` containing `PS1 mice.md`.

## Impact

- Orphan detection reports the fragment files as orphans
- Wiki links referencing the full title resolve incorrectly
- The notes/ directory loses its flat structure invariant

## Root cause

/reduce extracts scientifically accurate titles from literature without sanitizing filesystem-unsafe characters before writing.

## Fix (2026-02-23)

Three-layer prevention:

1. **validate_write.py hook** -- blocks writes to notes/, hypotheses/, literature/, experiments/ that create nesting (detects 3+ path components)
2. **sanitize_title() in schema_validator.py** -- replaces `/\:*?"<>|` with `-`, available for any code path
3. **CLAUDE.md title rules** -- explicitly lists `/` as banned, with biology-notation examples (APP-PS1, APOE3-3)

## Convention

Use `-` instead of `/` in all claim titles: APP-PS1, APOE3-3, Abeta42-40, AhR-NF-kappaB-NLRP3, insulin-IGF1, amyloid-tau, p-tau-Abeta42.
