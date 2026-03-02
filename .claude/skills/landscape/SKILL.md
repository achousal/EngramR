---
name: landscape
description: Map the hypothesis space to identify clusters, gaps, and redundancies
context: fork
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - Write
---

# /landscape -- Proximity / Clustering Agent

Map the hypothesis space to identify clusters, gaps, and redundancies.

## Architecture
Implements the Proximity agent from the co-scientist system (arXiv:2502.18864).

## Vault paths
- Hypotheses: `_research/hypotheses/`
- Landscape index: `_research/landscape.md`
- Per-goal landscapes: `_research/landscape/{goal-slug}.md`

## Code
- `_code/src/engram_r/hypothesis_parser.py` -- parse all hypothesis notes
- `_code/src/engram_r/obsidian_client.py` -- vault I/O

## Workflow
1. Read all hypothesis notes for the active research goal.
2. Analyze and cluster by:
   - Shared tags and domain keywords
   - Common assumptions
   - Similar mechanisms or pathways
   - Overlapping literature citations
   - Similar Elo tier
3. Generate the landscape summary.
4. Write to `_research/landscape/{goal-slug}.md` (per-goal file).
5. Update `_research/landscape.md` index table with goal entry.
6. If a `project_tag` is set on the research goal, filter hypotheses to those tagged with it.
7. Present findings to user.

## Landscape output format
Update `_research/landscape.md` with:

### Clusters
For each cluster:
- Cluster name (descriptive)
- Member hypotheses (wiki-links)
- Common theme
- Average Elo
- Distinguishing feature

### Gaps
- Research areas with no hypotheses
- Under-explored mechanism types
- Missing connections between clusters
- Suggested directions for /generate

### Redundancies
- Near-duplicate hypotheses (flag for potential merge via /evolve)
- Hypotheses with identical assumptions but different framing

### Suggested Directions
- Specific prompts for /generate to fill gaps
- Specific prompts for /evolve combination mode

## Rules
- Base clustering on content analysis, not just tags.
- Identify at least one gap if possible.
- Flag redundancies explicitly.
- Output should be actionable for /generate and /evolve.

## Skill Graph
Invoked by: /research
Invokes: (none -- leaf agent)
Reads: _research/hypotheses/
Writes: _research/landscape/, _research/landscape.md

## Rationale
Inductive gap analysis -- pattern recognition across the hypothesis space to identify clusters, redundancies, and under-explored regions. Directs /generate toward productive new areas.
