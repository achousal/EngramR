> **Historical note:** This document describes the original design rationale. Bioinformatics references reflect the original use case; the system is now domain-agnostic via profiles.

---
description: How this knowledge system was derived -- enables architect and reseed commands
created: 2026-02-21
engine_version: "0.8.0"
---

# System Derivation

## Configuration Dimensions

| Dimension | Position | Conversation Signal | Confidence |
|-----------|----------|--------------------|--------------------|
| Granularity | Atomic | "go ahead with research preset" -- explicit preset selection; existing atomic hypothesis notes confirm fit | High |
| Organization | Flat | Research preset default; existing flat vault structure | High |
| Linking | Explicit + implicit | Research preset default; bioinformatics domain benefits from cross-vocabulary discovery | High |
| Processing | Heavy | Research preset default; existing heavy co-scientist pipeline (generate-debate-evolve) | High |
| Navigation | 3-tier | Research preset default; hub -> domain topic maps -> individual claims | High |
| Maintenance | Condition-based | Research preset default | High |
| Schema | Moderate | Research preset default | High |
| Automation | Full | Research preset + Claude Code platform with existing hooks | High |

## Personality Dimensions

| Dimension | Position | Signal |
|-----------|----------|--------|
| Warmth | clinical | default -- research domain |
| Opinionatedness | neutral | default -- research conclusions are the user's |
| Formality | formal | default -- research domain |
| Emotional Awareness | task-focused | default -- intellectual domain |

## Vocabulary Mapping

| Universal Term | Domain Term | Category |
|---------------|-------------|----------|
| notes/ | notes/ | folder |
| inbox/ | inbox/ | folder |
| archive/ | archive/ | folder |
| note | claim | note type |
| note_plural | claims | note type |
| reduce | reduce | process phase |
| reflect | reflect | process phase |
| reweave | reweave | process phase |
| verify | verify | process phase |
| validate | validate | process phase |
| rethink | rethink | process phase |
| MOC | topic map | navigation |
| topic_map | topic map | navigation |
| hub | hub | navigation |
| description | claim context | schema field |
| topics | research areas | schema field |
| relevant_notes | relevant claims | schema field |
| orient | orient | session phase |
| persist | persist | session phase |
| processing | pipeline | workflow |
| wiki link | connection | link type |
| self/ space | research identity | space |

## Extraction Categories

| Category | What to Find | Output Type |
|----------|-------------|-------------|
| claims | Testable assertions about mechanisms, effects, or relationships | claim |
| evidence | Data points, measurements, statistical results supporting or refuting claims | claim |
| methodology-comparisons | How different studies approached similar questions | claim |
| contradictions | Results or interpretations that conflict with existing claims | claim |
| open-questions | Gaps in evidence, unresolved mechanisms, future directions | claim |
| design-patterns | Reusable experimental designs, analytical approaches, pipelines | claim |

## Platform

- Tier: Claude Code
- Automation level: full
- Hooks: Python (existing co-scientist) + bash (arscontexta)
- Skills: 12 existing co-scientist + 16 arscontexta processing

## Active Feature Blocks

- [x] wiki-links -- always included (kernel)
- [x] atomic-notes -- included (research preset)
- [x] mocs -- included (research preset, 3-tier navigation)
- [x] processing-pipeline -- always included
- [x] schema -- always included
- [x] maintenance -- always included
- [x] self-evolution -- always included
- [x] methodology-knowledge -- always included
- [x] session-rhythm -- always included
- [x] templates -- always included
- [x] ethical-guardrails -- always included
- [x] helper-functions -- always included
- [x] graph-analysis -- always included
- [x] semantic-search -- included (qmd 1.0.7 available)
- [ ] personality -- excluded (neutral-helpful default; no signals for personality)
- [x] self-space -- included (self/ already exists with co-scientist identity)
- [ ] multi-domain -- excluded (single domain: bioinformatics research)

## Coherence Validation Results

- Hard constraints checked: 3. Violations: none
  - atomic + 3-tier nav + high volume: OK (3-tier provides sufficient depth)
  - full automation + claude-code platform: OK (platform supports hooks and skills)
  - heavy processing + full automation: OK (pipeline skills present)
- Soft constraints checked: 7. Auto-adjusted: none. User-confirmed: none.
  - atomic + heavy processing: coherent (correct pairing)
  - moderate schema + full automation: good fit
  - explicit+implicit linking + semantic search: OK -- qmd available for semantic retrieval
- Compensating mechanisms active: MOC navigation + ripgrep + qmd semantic search

## Failure Mode Risks

1. **Collector's Fallacy** (HIGH) -- bioinformatics literature is abundant; inbox can grow indefinitely
2. **Orphan Drift** (HIGH) -- high creation volume during literature review phases
3. **Verbatim Risk** (HIGH) -- dense source material tempts summarization over transformation
4. **MOC Sprawl** (HIGH) -- bioinformatics topics proliferate (multi-omics, disease subtypes, methods)
5. **Productivity Porn** (HIGH) -- co-scientist + arscontexta dual system creates meta-work temptation

## Generation Parameters

- Folder names: notes/, inbox/, archive/, _code/templates/, manual/
- Skills to generate: reduce, reflect, reweave, verify, validate, seed, ralph, pipeline, tasks, stats, graph, next, learn, remember, rethink, refactor
- Hooks to generate: session-orient.sh, session-capture.sh, validate-note.sh, auto-commit.sh (additive merge with existing Python hooks)
- Templates to create: claim-note.md, topic-map.md
- Topology: single-agent with fresh-context per skill invocation

## Existing System Integration

This vault has a pre-existing co-scientist system that is preserved:
- 12 co-scientist skills: /research, /generate, /review, /tournament, /evolve, /landscape, /meta-review, /literature, /plot, /eda, /experiment, /project
- 4 Python hooks: session_orient.py, validate_write.py, auto_commit.py, session_capture.py
- Domain-specific directories: _research/hypotheses/, _research/literature/, _research/experiments/, _research/eda-reports/
- Co-scientist templates in _code/templates/

The arscontexta system adds the general knowledge processing layer alongside the co-scientist research layer.

## Domain Generalization (2026-03-01)

The system was generalized from bioinformatics-specific to domain-agnostic. Search backends, PII patterns, confounders, and heuristics are now configured via domain profiles (`_code/profiles/`). The bioinformatics profile remains the reference implementation. Core infrastructure (search_interface, pii_filter, literature skill) dispatches to profile-configured backends rather than hardcoding PubMed/arXiv.
