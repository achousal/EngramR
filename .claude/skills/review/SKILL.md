---
name: review
description: Critically evaluate hypotheses through multiple review lenses
context: fork
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - Write
---

# /review -- Multi-Mode Hypothesis Review Agent

Critically evaluate hypotheses through multiple review lenses.

## Dynamic context

Latest meta-review feedback (if available):
!`ls -t "$VAULT_ROOT/_research/meta-reviews/"*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No meta-reviews yet."`

## Architecture
Implements the Reflection agent from the co-scientist system (arXiv:2502.18864). Supports 6 review modes.

## Vault paths
- Hypotheses: `_research/hypotheses/`
- Meta-reviews: `_research/meta-reviews/`

## Code
- `_code/src/engram_r/hypothesis_parser.py` -- parse and update hypothesis notes
- `_code/src/engram_r/search_interface.py` -- unified search interface; dispatches to configured backends
- `_code/src/engram_r/obsidian_client.py` -- vault I/O

## Workflow
1. Ask user which hypothesis to review (or review all unreviewed).
2. Ask which review mode(s) to apply.
3. For each hypothesis and mode:
   a. Read the hypothesis note.
   b. Apply the review mode.
   c. Update `review_scores` in frontmatter (1-10 scale).
   d. Add any `review_flags` (e.g., "assumption-X-contradicted").
   e. Append a timestamped review entry to "## Review History".
4. Present findings to user.

## Review modes

### 1. Quick screen
- Rapid assessment without external tools.
- Score: novelty, correctness, testability, impact, overall (1-10 each).
- Flag obvious issues.

### 2. Literature review
- Search configured literature backends for the hypothesis claim.
- Flag if hypothesis is already published, partially known, or contradicted.
- Update review_flags accordingly.

### 3. Deep verification
- Decompose hypothesis into constituent assumptions.
- For each assumption, search for supporting/contradicting evidence.
- Flag invalid or unsupported assumptions.

### 4. Observation review
- User provides experimental data or observations.
- Assess whether the hypothesis explains the data better than alternatives.
- Score based on explanatory power.

### 5. Simulation review
- Walk through the proposed mechanism step by step.
- Identify failure modes, bottlenecks, implausible steps.
- Assess logical consistency.

### 6. Tournament-informed review
- Read latest meta-review patterns.
- Apply learned critique themes from previous tournaments.
- Score based on patterns that distinguish winners from losers.

## Review entry format (appended to Review History)
```
### {YYYY-MM-DD} {Mode Name}
**Scores**: novelty={N}, correctness={N}, testability={N}, impact={N}, overall={N}
**Flags**: {list or "none"}
**Summary**: {2-3 sentence assessment}
**Key concerns**: {bullet list}
```

## Project scoping
If a `project_tag` is set on the active research goal, filter hypotheses to those tagged with it when reviewing "all unreviewed". This prevents cross-project hypothesis mixing during batch reviews.

## Rules
- Always present review results to user before saving.
- Update both frontmatter scores and the Review History section.
- For literature review mode, cite source identifiers (PMIDs, arXiv IDs, URLs, as applicable to backend).
- review_scores use 1-10 scale (null = unreviewed).
- Aggregate overall score as weighted mean: correctness 30%, testability 25%, novelty 25%, impact 20%.

## Skill Graph
Invoked by: /research
Invokes: (none -- leaf agent)
Reads: _research/hypotheses/, _research/meta-reviews/
Writes: _research/hypotheses/ (frontmatter: review_scores, review_flags, Review History section)

## Rationale
Critical peer review -- deductive verification of hypothesis consistency and evidence fit. Provides the quality signal that drives tournament rankings and evolution priorities.
