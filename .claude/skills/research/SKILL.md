---
name: research
description: Orchestrate the co-scientist generate-debate-evolve loop
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Skill
  - TaskCreate
  - TaskUpdate
  - TaskList
---

# /research -- Supervisor / Orchestrator

Orchestrate the co-scientist generate-debate-evolve loop interactively.

## Architecture
This skill implements the Supervisor agent from the co-scientist architecture (arXiv:2502.18864). It defines research goals and coordinates other agent skills.

## Vault paths
- Research goals: `_research/goals/`
- Template: `_code/templates/research-goal.md`
- Vault root: repository root (detected automatically)

## Code
- `_code/src/engram_r/note_builder.py` -- `build_research_goal_note()`
- `_code/src/engram_r/obsidian_client.py` -- vault I/O
- `_code/src/engram_r/hypothesis_parser.py` -- parse hypothesis notes

## Workflow

### Setting a research goal
1. Ask the user for their research question or goal in natural language.
2. Clarify: domain, constraints, evaluation criteria, key background.
3. Build a research goal note using `build_research_goal_note()`.
4. Save to `_research/goals/{slug}.md`.
5. Present the co-scientist menu.

### Co-scientist menu
After each operation, return to this menu:
- **Generate** -- Create new hypotheses (invoke /generate)
- **Review** -- Critically review hypotheses (invoke /review)
- **Tournament** -- Run Elo-ranked pairwise debates (invoke /tournament)
- **Evolve** -- Refine top hypotheses (invoke /evolve)
- **Landscape** -- Map hypothesis space clusters/gaps per goal (invoke /landscape, writes to `_research/landscape/{goal-slug}.md`)
- **Meta-review** -- Synthesize patterns for self-improvement (invoke /meta-review)
- **Leaderboard** -- Show current Elo rankings from _research/hypotheses/_index.md
- **Literature** -- Search and add papers (invoke /literature)

### Self-improving loop
Before invoking any sub-skill, check `_research/meta-reviews/` for the latest meta-review note. If one exists, include its "Recommendations for Generation" or "Recommendations for Evolution" content as context for the sub-skill.

## State tracking
- Read `_research/goals/` to find the active research goal.
- Read `_research/hypotheses/_index.md` for current leaderboard. **If `_index.md` does not exist, create it** with frontmatter (`description: "Elo-ranked hypothesis leaderboard and generation index"`, `type: moc`, `created: {today}`), a `# Hypothesis Leaderboard` heading, an empty `## Rankings` table (`| Rank | Hypothesis | Elo | Goal | Gen | Status |`), and a `## Recent Activity` section.
- Read latest `_research/meta-reviews/*.md` for feedback loop.

## Rules
- Always present results to the user and wait for approval before proceeding.
- The user drives the loop -- never auto-advance to the next stage.
- Record which step was last completed so the user can resume.

## Skill Graph
Invoked by: user (entry point)
Invokes: /generate, /review, /tournament, /evolve, /landscape, /meta-review, /literature
Reads: _research/goals/, _research/hypotheses/_index.md, _research/meta-reviews/
Writes: _research/goals/

## Rationale
Research design and supervision. Selects the next method step to apply based on the current state of knowledge, closing the feedback loop between meta-review output and new generation cycles.
