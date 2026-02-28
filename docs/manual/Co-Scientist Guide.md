---
type: guide
title: Co-Scientist EngramR Guide
created: 2026-02-21
---

# Co-Scientist EngramR Guide

A multi-agent generate-debate-evolve system for hypothesis research, implemented as Claude Code skills + this Obsidian vault. Inspired by Google DeepMind's "Towards an AI co-scientist" (arXiv:2502.18864).

## Setup

```bash
cd _code
cp .env.example .env
# Fill in: OBSIDIAN_API_KEY, NCBI_API_KEY, NCBI_EMAIL
```

Requires the Obsidian Local REST API plugin (already installed).

## Core Workflow

Start with `/research` -- the orchestrator. It will:
1. Ask for a research question
2. Save a research goal note to the vault
3. Present a menu to drive the generate-debate-evolve loop

From there, cycle through these commands interactively:

| Step | Command | What it does |
|---|---|---|
| 1 | `/generate` | Creates new hypothesis notes (4 modes: de novo, literature-seeded, gap-filling, cross-goal) |
| 2 | `/review` | Reviews hypotheses with scores and flags (6 review modes) |
| 3 | `/tournament` | Pairwise debates between hypotheses, updates Elo ratings |
| 4 | `/meta-review` | Synthesizes patterns from debates -- feeds back into steps 1-3 |
| 5 | `/evolve` | Refines top hypotheses into stronger versions |
| 6 | `/landscape` | Maps clusters and gaps in the hypothesis space |

Each command is interactive -- it shows results and waits for approval before writing anything.

## Supporting Commands

- `/literature` -- Search PubMed/arXiv, save structured notes to `_research/literature/`
- `/eda` -- Run EDA on a dataset (auto-redacts PII columns), saves report to `eda-reports/`
- `/plot` -- Generate figures using the canonical theme from [[PLOT_DESIGN]]
- `/experiment` -- Log experiments linked to hypotheses

## Where Things Live

| Location | Contents |
|---|---|
| `_research/hypotheses/_index.md` | Elo leaderboard of all hypotheses |
| `_research/hypotheses/` | Individual hypothesis notes with frontmatter tracking Elo, generation, review scores |
| `_research/goals/` | Research goal definitions |
| `_research/tournaments/` | Match logs from pairwise debates |
| `_research/meta-reviews/` | Accumulated feedback that improves each cycle |
| `_research/landscape.md` | Cluster map of the hypothesis space |
| `_research/literature/` | Structured literature notes from PubMed/arXiv |
| `_research/experiments/` | Experiment logs linked to hypotheses |
| `eda-reports/` | EDA reports with auto-redacted PII |
| `_code/templates/` | Note templates for all 7 note types |
| `_code/` | Python/R code, tests, skill definitions |

## Example Session

```
/research
> "What early indicators predict treatment response independently of baseline severity?"
# Creates goal note, shows menu

/generate
# Pick "literature-seeded" mode
# Searches PubMed, proposes 3 hypotheses, approve each

/review
# Pick "plausibility" mode
# Scores each hypothesis on mechanistic coherence and biological plausibility

/tournament
# Run 3 pairwise matches, override any verdict
# Elo ratings update automatically

/meta-review
# Synthesizes what made winners win
# Feedback improves the next /generate and /review calls

/evolve
# Pick top hypothesis, evolve via "strengthen"
# New hypothesis enters the pool at Elo 1200
```

## The Self-Improving Loop

```
/research (set goal)
    |
    v
/generate --> new hypotheses (Elo=1200)
    |
    v
/review --> scores + flags on each hypothesis
    |
    v
/tournament --> pairwise debates, Elo updates
    |
    v
/meta-review --> synthesize patterns
    |               |
    v               v
/evolve         feedback into /generate
    |           and /review prompts
    v
/landscape --> cluster map, identify gaps
    |
    v
back to menu (you decide next step)
```

Each cycle gets better because `/meta-review` feeds patterns back into the other agents. The loop is human-driven -- it never auto-advances.

## Generation Modes (/generate)

1. **De novo** -- Generate hypotheses from first principles without external input
2. **Literature-seeded** -- Search PubMed/arXiv, identify gaps, propose hypotheses addressing them
3. **Gap-filling** -- Target unexplored regions identified by meta-review or landscape analysis
4. **Cross-goal** -- Combine insights across multiple research goals to find novel intersections

## Review Modes (/review)

1. **Plausibility** -- Assess mechanistic coherence and biological plausibility
2. **Novelty** -- PubMed/arXiv search to verify novelty claims against existing literature
3. **Testability** -- Evaluate whether the hypothesis can be tested with available methods and data
4. **Impact** -- Score potential significance if the hypothesis is validated
5. **Feasibility** -- Assess resource requirements, timeline, and practical constraints
6. **Overall** -- Comprehensive review combining all dimensions with weighted scoring

## Evolution Modes (/evolve)

1. **Strengthen** -- Fix flagged weaknesses with literature and evidence
2. **Merge** -- Combine best aspects of 2-3 top hypotheses into a unified version
3. **Pivot** -- Reframe the hypothesis by shifting its core mechanism or target
4. **Decompose** -- Split a complex hypothesis into independently testable sub-hypotheses
5. **Generalize** -- Abstract the hypothesis to apply across broader conditions or domains

## Hypothesis Note Format

Every hypothesis in `_research/hypotheses/` has YAML frontmatter tracking:
- `elo` -- Elo rating (starts at 1200)
- `generation` -- 1 = original, 2+ = evolved
- `parents` / `children` -- lineage links
- `review_scores` -- novelty, correctness, testability, impact, overall (1-10)
- `review_flags` -- issues flagged by /review
- `status` -- proposed, under-review, active, evolved, retired

## Running Tests

```bash
cd _code
uv run pytest tests/ -v --cov=engram_r   # run tests with coverage
uv run ruff check src/                        # lint
uv run black --check src/                     # format
```
