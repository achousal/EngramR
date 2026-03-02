---
description: Queue IDs and filenames derived from author names or non-ASCII titles must use NFC-normalized UTF-8, not JSON-escaped Unicode escape sequences
type: methodology
category: processing
source: session-mining
session_source: sessions 2026-02-22 queue state
created: 2026-02-23
status: active
---

# normalize unicode in queue IDs and filenames to NFC UTF-8

## What to Do

When constructing queue task IDs or filenames from source metadata (author names, paper titles, hypothesis labels), normalize the string to NFC UTF-8 before writing. In Python, use `unicodedata.normalize("NFC", text)`. In bash, pipe through `uconv -x NFC` or rely on locale-aware tools.

The canonical form is native characters: `garcía-gonzález`, not the JSON-escaped form `garc\u00eda-gonz\u00e1lez`.

Verify that any JSON serializer writes UTF-8 directly rather than ASCII-escaping non-Latin characters. In Python's `json.dump`, pass `ensure_ascii=False`.

## What to Avoid

Do not let filenames or IDs contain JSON Unicode escape sequences (`\uXXXX`). These are valid JSON but become literal `\u00ed` strings in filenames and queue lookups, breaking file resolution and queue ID matching.

Do not write queue IDs or filenames without normalizing the source string first -- author names from search backends frequently contain accented characters.

## Why This Matters

A queue entry written with an escaped ID (`garc\u00eda`) cannot be matched by a lookup using the normalized form (`garcía`). The mismatch breaks phase progression tracking: the queue reports the task as pending even though the file was created. Correcting this required a manual commit to rewrite queue state.

## Scope

Applies to all code paths that write to `ops/queue/queue.json`, `ops/queue/*.md` task files, and any filename derived from non-ASCII source metadata (author names, paper titles with accented characters, hypothesis labels). Also applies to YAML frontmatter values that are used as IDs or cross-references.

---

Related: [[methodology]]
