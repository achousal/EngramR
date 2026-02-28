---
name: generate
description: Produce novel, literature-grounded hypotheses for a research goal
context: fork
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - Write
---

# /generate -- Hypothesis Generation Agent

Produce novel, literature-grounded hypotheses for a research goal.

## Dynamic context

Latest meta-review feedback (if available):
!`ls -t "$VAULT_ROOT/_research/meta-reviews/"*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No meta-reviews yet."`

Current landscape gaps (if available):
!`ls -t "$VAULT_ROOT/_research/landscape/"*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No landscape analysis yet."`

## Architecture
Implements the Generation agent from the co-scientist system (arXiv:2502.18864). Supports 4 generation modes.

## Vault paths
- Output: `_research/hypotheses/` (new hypothesis notes)
- Research goals: `_research/goals/`
- Meta-reviews: `_research/meta-reviews/`

## Code
- `_code/src/engram_r/note_builder.py` -- `build_hypothesis_note()`
- `_code/src/engram_r/hypothesis_parser.py` -- `build_hypothesis_frontmatter()`
- `_code/src/engram_r/pubmed.py` -- literature search
- `_code/src/engram_r/arxiv.py` -- arXiv search
- `_code/src/engram_r/obsidian_client.py` -- vault I/O

## Workflow
1. Read the active research goal from `_research/goals/`.
2. Read the latest meta-review (if exists) for feedback.
3. Read existing hypotheses to avoid duplication.
4. Ask the user which generation mode to use.
5. Generate hypotheses according to the selected mode.
6. Present each hypothesis to the user for approval before saving.
7. Save approved hypotheses to `_research/hypotheses/hyp-{date}-{NNN}.md` with Elo=1200, generation=1.
8. Update `_research/hypotheses/_index.md`.

## Generation modes

### 1. Literature synthesis
- Search PubMed/arXiv for papers relevant to the research goal.
- Identify gaps, contradictions, or unexplored connections.
- Propose hypotheses that address these gaps.
- Ground each hypothesis with specific citations.

### 2. Self-play debate
- Simulate 2-3 expert perspectives (e.g., experimentalist, theorist, statistician).
- Each expert proposes and critiques hypotheses from their viewpoint.
- Extract the most promising novel ideas from the debate.

### 3. Assumption-based reasoning
- Take an existing hypothesis (user selects which).
- Enumerate its key assumptions.
- For each assumption: generate an alternative hypothesis where that assumption is relaxed, inverted, or replaced.

### 4. Research expansion
- Read meta-review feedback and existing top hypotheses.
- Identify under-explored regions of the hypothesis space.
- Generate hypotheses specifically targeting those gaps.
- Use the landscape map if available.

## Project scoping
If the active research goal has a `project_tag` field set, inherit it into generated hypothesis tags. This enables filtering hypotheses by project across the vault.

## Hypothesis format
Each hypothesis note must include:
- Frontmatter: type, title, id, status=proposed, elo=1200, generation=1, research_goal link, tags (include `project_tag` from goal if set)
- Sections: Statement, Mechanism, Literature Grounding, Testable Predictions, Proposed Experiments, Assumptions, Limitations & Risks, Review History, Evolution History

## ID format
`hyp-{YYYYMMDD}-{NNN}` where NNN is a zero-padded sequence number for that day.

## Rules
- Every hypothesis must have at least 2 testable predictions.
- Every hypothesis must list its key assumptions explicitly.
- Literature grounding should cite specific papers (PMID or arXiv ID).
- Check existing hypotheses to ensure novelty.
- Present each hypothesis for user approval before saving.
- Include meta-review feedback in the generation prompt when available.

## Skill Graph
Invoked by: /research
Invokes: (none -- leaf agent)
Reads: _research/goals/, _research/meta-reviews/, _research/landscape/, _research/hypotheses/
Writes: _research/hypotheses/, _research/hypotheses/_index.md

## Rationale
Abductive inference -- generating the best explanatory hypotheses from available evidence. Exists as the creative engine that proposes novel ideas grounded in literature, filling gaps identified by /landscape and incorporating feedback from /meta-review.
