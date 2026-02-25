---
description: Why each configuration dimension was chosen -- the reasoning behind initial system setup
category: derivation-rationale
created: 2026-02-21
status: active
---

# derivation rationale for bioinformatics research

This vault was derived on 2026-02-21 using the Research preset on the Claude Code platform. The user explicitly selected the Research preset for a bioinformatics and computational biology domain, confirming the atomic-granularity, heavy-processing, full-automation configuration.

## Key Dimension Choices

**Granularity: Atomic** -- The existing co-scientist system already produces atomic hypothesis notes. Extending this to general research claims maintains consistency. One claim per file maximizes composability for cross-source comparison in multi-omics and biomarker discovery work.

**Organization: Flat** -- The vault already uses flat directories (hypotheses/, literature/, experiments/). Wiki-link graph navigation is preferred over folder hierarchy, consistent with the Zettelkasten tradition the research preset draws from.

**Processing: Heavy** -- The existing co-scientist pipeline (generate-debate-evolve) is already heavy processing. The arscontexta pipeline (reduce-reflect-reweave-verify) extends this to general literature processing with the same depth.

**Navigation: 3-tier** -- Hub -> domain topic maps -> individual claims. Necessary given projected volume from literature review in bioinformatics.

**Automation: Full** -- Claude Code platform supports hooks and skills. The existing system already uses Python hooks for session orientation, schema validation, auto-commit, and session capture. The arscontexta layer adds bash hooks merged additively.

**Self-space: Enabled** -- The existing vault has self/identity.md and self/methodology.md from the co-scientist setup. These are preserved and extended with self/goals.md.

**Semantic search: Active** -- qmd 1.0.7 installed. Available for semantic retrieval alongside MOC navigation and ripgrep.

## Coherence Validation

All hard constraints passed. No soft warnings remaining -- semantic search now active via qmd.

## Failure Mode Awareness

The bioinformatics research domain is HIGH risk for: Collector's Fallacy (abundant literature), Orphan Drift (high creation volume), Verbatim Risk (dense source material), MOC Sprawl (proliferating topics), and Productivity Porn (dual-system meta-work temptation).

---

Topics:
- [[methodology]]
