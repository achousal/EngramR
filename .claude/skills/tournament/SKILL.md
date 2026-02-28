---
name: tournament
description: Rank hypotheses through pairwise scientific debate with Elo ratings
context: fork
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - Write
---

# /tournament -- Elo Tournament Ranking Agent

Rank hypotheses through pairwise scientific debate with Elo ratings.

## Architecture
Implements the Ranking/Tournament agent from the co-scientist system (arXiv:2502.18864).

## Vault paths
- Hypotheses: `_research/hypotheses/`
- Match logs: `_research/tournaments/`
- Template: `_code/templates/tournament-match.md`
- Leaderboard: `_research/hypotheses/_index.md`

## Code
- `_code/src/engram_r/elo.py` -- `compute_elo()`, `generate_matchups()`
- `_code/src/engram_r/hypothesis_parser.py` -- read/update hypothesis notes
- `_code/src/engram_r/note_builder.py` -- `build_tournament_match_note()`
- `_code/src/engram_r/obsidian_client.py` -- vault I/O

## Workflow
1. Read all hypotheses for the active research goal.
2. Generate matchups using `generate_matchups()` -- prioritizes under-matched and similar-Elo pairs.
3. Ask user how many matches to run this round.
4. For each match:
   a. Present both hypotheses side by side.
   b. Conduct structured debate across dimensions: novelty, correctness, testability, impact.
   c. Determine winner with justification.
   d. Present verdict to user -- user can override.
   e. Compute Elo changes via `compute_elo()`.
   f. Update both hypothesis frontmatter: elo, matches, wins/losses.
   g. Save match log to `_research/tournaments/{date}-{match_id}.md`.
5. Update `_research/hypotheses/_index.md` leaderboard table (sorted by Elo descending).
6. Show updated leaderboard to user.

## Tiered comparison
- Top 25% by Elo: multi-turn debate (deeper analysis, consider edge cases, examine assumptions).
- Bottom 75%: single-turn pairwise comparison (quicker assessment).

## Elo system
- Starting Elo: 1200
- K-factor: 32 (default)
- Rating sum is preserved across matches.
- Use `expected_score()` for probability calculations.

## Match log format
Frontmatter: type=tournament-match, date, research_goal, hypothesis_a, hypothesis_b, winner, elo_change_a, elo_change_b.
Sections: Debate Summary, Novelty Comparison, Correctness, Testability, Impact, Verdict, Justification.

## Leaderboard format (in _research/hypotheses/_index.md)
| Rank | ID | Title | Elo | Gen | Status | Matches |
Sorted by Elo descending. Updated after each tournament round.

## Federated mode (`--federated`)

When invoked with `--federated`, the tournament includes `type: foreign-hypothesis`
notes imported from peer vaults via `/federation-sync`.

Key differences from local mode:
- Matches update `elo_federated` and `matches_federated` instead of `elo` and `matches`.
- Local hypotheses also get `elo_federated` / `matches_federated` fields added on first
  federated match (starting at their current `elo` value).
- Match logs include `mode: federated` in frontmatter.
- Leaderboard is written to `_research/hypotheses/_federated-leaderboard.md` (separate
  from the local `_index.md` leaderboard).
- Foreign hypotheses are read-only -- their `elo` (source vault rating) is never modified.

This keeps local and federated rankings independent. A hypothesis can rank #1 locally
but #5 in federated competition (or vice versa).

## Rules
- Always let the user override the verdict.
- Verify Elo sum preservation after each match.
- Log every match -- no unrecorded debates.
- Present matches one at a time with full context.

## Skill Graph
Invoked by: /research
Invokes: (none -- leaf agent)
Reads: _research/hypotheses/, _research/goals/
Writes: _research/tournaments/, _research/hypotheses/ (frontmatter: elo, matches, wins, losses), _research/hypotheses/_index.md

## Rationale
Competitive falsification -- pairwise adversarial comparison forces relative ranking of hypotheses. The Elo system produces a stable ordering that surfaces the strongest ideas for evolution and identifies weak ones for pruning.
