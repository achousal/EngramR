---
name: evolve
description: Refine and evolve top-ranked hypotheses into stronger versions
context: fork
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - Write
---

# /evolve -- Hypothesis Evolution Agent

Refine and evolve top-ranked hypotheses into stronger versions.

## Dynamic context

Latest meta-review feedback (if available):
!`ls -t "$VAULT_ROOT/_research/meta-reviews/"*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No meta-reviews yet."`

## Architecture
Implements the Evolution agent from the co-scientist system (arXiv:2502.18864). Supports 5 evolution modes.

## Vault paths
- Hypotheses: `_research/hypotheses/`
- Meta-reviews: `_research/meta-reviews/`

## Code
- `_code/src/engram_r/note_builder.py` -- `build_hypothesis_note()`
- `_code/src/engram_r/hypothesis_parser.py` -- parse and link hypotheses
- `_code/src/engram_r/search_interface.py` -- unified search interface; dispatches to configured backends
- `_code/src/engram_r/obsidian_client.py` -- vault I/O

## Workflow
1. Read existing hypotheses and their Elo rankings.
2. Read latest meta-review for evolution guidance.
3. Ask user which hypothesis/hypotheses to evolve and which mode.
4. Generate evolved hypothesis.
5. Present to user for approval.
6. Save as new note with generation=N+1, parents=[parent IDs], Elo=1200.
7. Update parent hypothesis: add child link, optionally set status to "evolved".
8. Update `_research/hypotheses/_index.md`.

## Evolution modes

### 1. Grounding enhancement
- Read review flags and weaknesses from /review.
- Search literature to address specific concerns.
- Strengthen reasoning and evidence base.
- Fix flagged assumptions.

### 2. Combination
- Select 2-3 top hypotheses.
- Identify complementary strengths.
- Merge into a unified hypothesis that combines the best aspects.
- Resolve any contradictions between parents.

### 3. Simplification
- Reduce complexity of the hypothesis.
- Strip non-essential assumptions.
- Focus on the most testable core claim.
- Improve experimental feasibility.

### 4. Research extension
- Extend hypothesis to adjacent domains.
- Explore broader implications.
- Connect to related fields or mechanisms.

### 5. Divergent exploration
- Deliberately move away from current hypothesis clusters.
- Generate contrarian or orthogonal alternatives.
- Challenge prevailing assumptions in the research goal.
- Use landscape map (if available) to identify empty regions.

## Evolved hypothesis rules
- generation = max(parent generations) + 1
- parents = [list of parent hypothesis IDs]
- Elo starts at 1200 (must earn ranking through tournament)
- Status = "proposed" (enters the tournament pool)
- Must clearly document what changed and why in "Evolution History" section
- Must inherit relevant literature grounding from parents

## Rules
- Always present evolved hypothesis to user before saving.
- Always link parent <-> child bidirectionally.
- Include meta-review feedback in evolution prompts.
- Document the evolution rationale in both parent and child notes.

## Skill Graph
Invoked by: /research
Invokes: (none -- leaf agent)
Reads: _research/hypotheses/, _research/meta-reviews/
Writes: _research/hypotheses/ (new generation notes), _research/hypotheses/_index.md

## Rationale
Theory refinement through synthesis -- combines strengths of existing hypotheses and addresses weaknesses identified by /review and /tournament. Ensures the hypothesis pool improves across generations.
