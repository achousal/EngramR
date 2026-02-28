---
name: meta-review
description: Synthesize patterns from tournament debates and reflection reviews
context: fork
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - Write
---

# /meta-review -- Meta-Review / Pattern Synthesis Agent

Synthesize patterns from tournament debates and reflection reviews into actionable feedback.

## Dynamic context

Recent tournament match logs:
!`ls -t "$VAULT_ROOT/_research/tournaments/"*.md 2>/dev/null | head -5 | xargs cat 2>/dev/null || echo "No tournament matches yet."`

Previous meta-review (if available):
!`ls -t "$VAULT_ROOT/_research/meta-reviews/"*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No previous meta-reviews."`

## Architecture
Implements the Meta-Review agent from the co-scientist system (arXiv:2502.18864). This is the key feedback mechanism that enables the self-improving loop.

## Vault paths
- Tournament logs: `_research/tournaments/`
- Hypotheses: `_research/hypotheses/` (for review history)
- Output: `_research/meta-reviews/{date}.md`
- Template: `_code/templates/meta-review.md`

## Code
- `_code/src/engram_r/note_builder.py` -- `build_meta_review_note()`
- `_code/src/engram_r/hypothesis_parser.py` -- parse hypothesis review histories
- `_code/src/engram_r/obsidian_client.py` -- vault I/O

## Workflow
1. Read all recent tournament match logs from `_research/tournaments/`.
2. Read review histories from all hypothesis notes.
3. Analyze patterns across both sources.
4. Generate meta-review note.
5. Save to `_research/meta-reviews/{YYYY-MM-DD}.md`.
6. Present findings to user.

## Pattern analysis

### Recurring Weaknesses
- Common critique themes across hypotheses.
- Frequently flagged assumptions.
- Typical failure modes in debates.

### Key Literature
- Papers cited most frequently across hypotheses and debates.
- Papers that consistently differentiate winners from losers.
- Foundational references the research area depends on.

### Invalid Assumptions
- Assumptions flagged as invalid across multiple hypotheses.
- Assumptions that consistently lead to losses in tournaments.

### Winner Patterns
- What do winning hypotheses have in common?
- Which review dimensions (novelty, correctness, testability, impact) matter most?
- What level of specificity tends to win?

### Recommendations for Generation
Concrete advice for /generate:
- What types of hypotheses are missing?
- What grounding is needed?
- What assumptions should new hypotheses avoid?

### Recommendations for Evolution
Concrete advice for /evolve:
- Which weaknesses should evolution address first?
- Which combination opportunities exist?
- What simplifications would be valuable?

## The self-improving loop
This meta-review output is read by:
- /generate (via "Read latest meta-review" step)
- /review (via "Tournament-informed review" mode)
- /evolve (via "Read latest meta-review" step)
- /research (to inform next steps)

This creates a feedback loop where each cycle of generate-debate-evolve-meta-review improves the quality of subsequent cycles without any model fine-tuning.

## Rules
- Always cite specific match IDs and hypothesis IDs when identifying patterns.
- Recommendations must be concrete and actionable.
- Compare current meta-review to previous ones to track improvement.
- Present findings to user before saving.

## Skill Graph
Invoked by: /research
Invokes: (none -- leaf agent)
Reads: _research/tournaments/, _research/hypotheses/ (review histories)
Writes: _research/meta-reviews/

## Rationale
Second-order learning -- meta-analysis of the review and debate process itself. Extracts actionable patterns that feed back into /generate, /review, and /evolve, making each cycle more effective than the last.
