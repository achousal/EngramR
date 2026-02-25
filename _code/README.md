# Co-Scientist EngramR

A multi-agent generate-debate-evolve system for hypothesis research, implemented as Claude Code skills + Obsidian vault. Inspired by Google DeepMind's "Towards an AI co-scientist" (arXiv:2502.18864).

## Quick start

```bash
cd _code
uv sync --all-extras
cp .env.example .env   # fill in OBSIDIAN_API_KEY, NCBI_API_KEY, NCBI_EMAIL
uv run pytest tests/ -v
```

For co-scientist architecture, vault structure, and the self-improving loop, see the [project README](../README.md).

## Library modules

All code in `src/engram_r/`:

| Module | Purpose |
|---|---|
| `obsidian_client.py` | REST API wrapper for Obsidian Local REST API |
| `note_builder.py` | Pure functions for building all note types |
| `hypothesis_parser.py` | Parse/update hypothesis YAML frontmatter + body |
| `elo.py` | Elo rating math (pure, no I/O) |
| `pii_filter.py` | PII/ID column detection and redaction |
| `plot_theme.py` | Matplotlib/seaborn theme, palettes, figure sizes |
| `plot_stats.py` | Statistical test selection, runners, formatters |
| `plot_builders.py` | Standard plot builders (violin, box, scatter, heatmap, volcano, forest, ROC, bar) |
| `pubmed.py` | NCBI EUTILS search |
| `arxiv.py` | arXiv Atom API search |
| `eda.py` | EDA computations + themed plots |
| `daemon_config.py` | Config dataclass for Research Loop Daemon |
| `daemon_scheduler.py` | Priority cascade scheduler -- reads vault state, outputs JSON task |
| `schema_validator.py` | Validate note frontmatter against known schemas |

R code in `R/`: `theme_research.R`, `palettes.R`, `stats_helpers.R`, `plot_builders.R`, `plot_helpers.R`.

## Testing

```bash
uv run pytest tests/ -v --cov=engram_r    # 344 tests, 92% coverage
uv run ruff check src/                         # lint
uv run black --check src/                      # format
```

## Automation Hooks

4 hooks in `scripts/hooks/`, configured in `.claude/settings.json`:

| Hook | Event | Mode | Purpose |
|---|---|---|---|
| `session_orient.py` | SessionStart | sync | Print active goals, top hypotheses, latest meta-review |
| `validate_write.py` | PostToolUse (Write/Edit) | sync | Block writes that violate note schemas |
| `auto_commit.py` | PostToolUse (Write/Edit) | async | Auto-commit vault note changes |
| `session_capture.py` | Stop | sync | Record session summary to `ops/sessions/` |

Disable any hook by setting its toggle to `false` in `ops/config.yaml`.

Smoke test commands:
```bash
# Orient
uv run python scripts/hooks/session_orient.py

# Validate (expects JSON on stdin)
echo '{"tool_name":"Write","tool_input":{"file_path":"...","content":"..."}}' | uv run python scripts/hooks/validate_write.py
```

## Hypothesis note format

YAML frontmatter tracks: id, status, elo, matches, wins, losses, generation, parents, children, review_scores, review_flags, linked_experiments, linked_literature.

Sections: Statement, Mechanism, Literature Grounding, Testable Predictions, Proposed Experiments, Assumptions, Limitations & Risks, Review History, Evolution History.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `OBSIDIAN_API_KEY` | Yes | Obsidian Local REST API bearer token |
| `OBSIDIAN_API_URL` | No | Default: `https://127.0.0.1:27124` |
| `NCBI_API_KEY` | Yes | NCBI EUTILS for 10 req/s |
| `NCBI_EMAIL` | Yes | Required by NCBI API policy |
| `VAULT_PATH` | No | Vault root for daemon, decision engine, registry |
| `SLACK_BOT_TOKEN` | Slack | Slack bot OAuth token (xoxb-...) |
| `SLACK_APP_TOKEN` | Slack | Slack app-level token for socket mode (xapp-...) |
| `SLACK_BOT_CHANNEL` | Slack | Default channel for bot posts |
| `SLACK_DEFAULT_CHANNEL` | Slack | Fallback channel for slack_client |
| `SLACK_TEAM_ID` | Slack | Workspace team ID |
| `ANTHROPIC_API_KEY` | Slack | Claude API key for Slack bot responses |

## Plot theme and reporting standards

Anchored to `_code/styles/STYLE_GUIDE.md` (descriptive, philosophy-driven).
- `_code/styles/STYLE_GUIDE.md`: visual philosophy, element-by-element conventions, stats, reporting standards, builders
- `docs/styles/elahi.md`, `docs/styles/chipuk.md`: lab-specific color palettes and policies
- Key theme values: 14pt base, bold titles, grey90 strips, bottom legend, left+bottom spines only
- Semantic palettes: direction, significance (universal); sex, dx, binary (Elahi -- see `docs/styles/elahi.md`)
- Lab palettes: Elahi (Set1), Chipuk (Okabe-Ito), Kuang (Set1)
- Output: PDF vector default, 300 DPI raster, sidecar p-values
- Stats: decision tree via `select_test()`, formatters via `format_pval()`
- Builders: `build_violin()`, `build_box()`, `build_scatter()`, etc.
- Python: `apply_research_theme()` + `save_figure()` + `plot_builders`
- R: `theme_research()` + `save_plot()` + `plot_builders.R`

### Analysis deliverables (per _code/styles/STYLE_GUIDE.md)

Every analysis script must produce: figures (PDF), p-value sidecars, stats report (txt), Table 1 (csv+png, if cohort-based), NA summary (csv, if any missingness). See _code/styles/STYLE_GUIDE.md "Analysis deliverables checklist" for the full table.

Key conventions:
- **n in plots**: always visible -- italic `n=N` at base of distribution plots, inline in scatter annotations
- **Test names**: always named in the stat annotation box (e.g., "Mann-Whitney p = 0.003")
- **Stats report**: timestamped txt with settings, sample counts, per-group results (AD_Chloe pattern)
- **Table 1**: CSV + rendered figure, mean(SD) / n(%), group n in column headers (DAC_CRF pattern)
- **NA summary**: CSV with variable, group, n_missing, pct_missing, record_ids (DAC_CRF pattern)
