---
description: "Symlinked project repos are indexed by Obsidian but their internal docs appear as graph orphans unless explicitly wiki-linked from a vault-native note"
category: process-pattern
status: active
created: 2026-02-23
---

## Problem

When a project is onboarded via `/onboard`, a symlink `_dev/{tag}` makes the external repo browsable from within Obsidian. Obsidian indexes all `.md` files under the symlink, so they become graph citizens. However, the onboard skill only creates one wiki-link bridge -- the `![[_dev/{tag}/CLAUDE.md]]` transclusion in the project note. Any other `.md` files in the repo (README, architecture docs, ADRs, investigation notes) have no incoming wiki-links from vault-native notes. They appear as orphans in the graph and are invisible to `/health` orphan detection because they live under `_dev/`.

## Mechanism

Obsidian resolves wiki-links by filename, not path. A file `_dev/celiac-risks/analysis/docs/ARCHITECTURE.md` is reachable as `[[ARCHITECTURE]]` from anywhere in the vault. But if no vault-native note contains that link, the file is indexed but disconnected -- a graph orphan that contributes nothing to navigation or discovery.

## Rule

Every symlinked project repo with internal `.md` documentation must have explicit wiki-link bridges from its project note to significant internal docs. The bridge lives in a `## Key Docs` section appended to the project note body, after the CLAUDE.md transclusion.

Each entry requires a context phrase explaining relevance (same convention as topic map Core Ideas):
```markdown
## Key Docs
- [[ARCHITECTURE]] -- system architecture and module boundaries
- [[README_FACTORIAL]] -- 2x2x2 factorial experiment design
```

## Enforcement

The `/onboard` skill enforces this via Step 5a2 (Internal Doc Discovery), which scans the project directory for `.md` files, presents them to the user as a checklist, and generates the Key Docs section for selected files. For already-onboarded projects, the bridge must be added manually or via `/onboard --update`.
