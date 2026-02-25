---
description: "Conventional commit messages used as YAML source or session_source values contain colons that break frontmatter parsing unless double-quoted"
type: "methodology"
category: "quality"
source: "session-mining"
session_source: "git commit ebf4b4e 2026-02-22"
created: "2026-02-23"
status: active
---

# commit message strings in yaml source fields require double-quoting

## What to Do

When populating `source`, `session_source`, or any YAML string field with a conventional commit message (e.g., `"docs: tighten EngramR prose"`, `"fix(yaml): harden frontmatter paths"`), always wrap the value in double quotes.

The colon in conventional commit type prefixes (`feat:`, `fix:`, `docs:`, `chore:`) is a YAML special character. An unquoted colon followed by a space starts a new key-value pair, silently corrupting the frontmatter.

Good:
```yaml
session_source: "git commit 8a88c3a -- docs: tighten EngramR prose"
source: "session-mining"
```

Bad:
```yaml
session_source: git commit 8a88c3a -- docs: tighten EngramR prose
```

## What to Avoid

Do not use commit message strings as YAML field values without quoting. This applies to:
- `source` fields that reference a git commit with a conventional type prefix
- `session_source` fields that quote commit hashes and messages
- Any inline commit reference that contains `:` followed by a space

Do not assume that because a string looks like a sentence it is YAML-safe. Colons are valid in English but structurally significant in YAML.

## Why This Matters

Commit `ebf4b4e` (2026-02-22) was created specifically to fix this class of failure. The validate_write hook caught the bad YAML and blocked the write, but this required a wasted retry turn each time the error occurred. The trigger was the observation that commit message `"docs: tighten am/pm references"` was being written into `session_source` fields without quoting, causing colons to break the frontmatter.

The general YAML Safety rule already exists in CLAUDE.md ("wrap every string value in double quotes"). This methodology note makes the specific failure mode concrete for memory mining and methodology review: the commit message colon is a common, recurring source of this error.

## Scope

Applies whenever writing raw markdown frontmatter in skills (/remember, /reduce, /seed, /rethink). The Python `note_builder` uses `yaml.dump()` with `ensure_ascii=False` which handles quoting automatically -- this rule applies only to skills that construct frontmatter as raw text.

---

Related: [[methodology]]
