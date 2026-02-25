# System Health & Reproducibility Audit Report

**Codebase:** EngramR `_code/`
**Date:** 2026-02-23 (verified 2026-02-23)
**Scope:** 20 Python modules, 5 R modules, 10 shell scripts, 4 hooks, 562 tests

---

## 1. Repo Map

### Execution Surface

```
ENTRYPOINTS
============
[Hooks - triggered by Claude Code]
  session_orient.py  --SessionStart--> stdout orientation text
  validate_write.py  --PostToolUse-->  block/allow decision (JSON)
  auto_commit.py     --PostToolUse-->  git add + commit (async)
  session_capture.py --Stop---------> ops/sessions/*.md

[Scripts - manual invocation]
  init_vault.py      --CLI--> full vault scaffold + git init
  batch_seed.py      --CLI--> ops/queue/*.md task files

[Daemon]
  daemon.sh          --loop--> reads vault state -> selects task -> runs claude
  daemon-all.sh      --tmux--> one daemon.sh per registered vault

[Shell Utilities]
  orphan-notes.sh, dangling-links.sh, backlinks.sh, link-density.sh,
  rename-note.sh, validate-schema.sh, create-dev-links.sh
```

### Internal Dependency Graph

```
Core I/O                    Visualization           Daemon / Decision
-----------                 ---------------         ------------------
obsidian_client             plot_theme <----+       daemon_config
  +-- vault_registry        plot_stats      |         |
  +-- hypothesis_parser     plot_builders --+       daemon_scheduler
                                                      +-- daemon_config
Note Building               Data / EDA                +-- hypothesis_parser
-----------                 ----------              decision_engine
note_builder (standalone)   pii_filter                +-- daemon_config
hypothesis_parser           eda                       +-- daemon_scheduler
schema_validator              +-- pii_filter          +-- vault_registry
                              +-- plot_theme
Federation                  Ratings                 API Clients
----------                  -------                 -----------
federation_config           elo (pure math)         pubmed (urllib)
claim_exchange                                      arxiv (urllib)
hypothesis_exchange
  +-- claim_exchange
```

**Circular dependencies:** None.
**God-modules (>10 dependents):** None. Max inbound is ~3.

### External Service Boundaries

| Boundary | Module | Protocol |
|----------|--------|----------|
| Obsidian REST API | obsidian_client | HTTPS (self-signed, SSL verify disabled) |
| NCBI EUTILS | pubmed | HTTPS |
| arXiv Atom API | arxiv | HTTP |
| Git CLI | auto_commit, rename-note.sh | subprocess |
| Filesystem | all hooks, daemon, eda, claim/hypothesis exchange | pathlib / bash |

### Security Notes on Service Boundaries

| Finding | Location | Severity | Detail |
|---------|----------|----------|--------|
| arXiv uses HTTP, not HTTPS | arxiv.py | [MED] | API calls over plaintext; upgrade to HTTPS endpoint |
| SSL verify disabled for Obsidian | obsidian_client.py | [LOW] | Expected for local self-signed cert; document the rationale |
| Shell injection via unescaped titles | rename-note.sh, backlinks.sh | [MED-HIGH] | User-provided titles passed to sed/grep without escaping; `.` `*` `+` `[` match unintended patterns; titles with shell metacharacters could cause command injection |

---

## 2. I/O Contracts Inventory

### Pure Modules (no I/O, fully idempotent)

| Module | Input | Output | Notes |
|--------|-------|--------|-------|
| elo | floats, dicts, seed | EloResult, matchup list | Seeded RNG |
| note_builder | strings, dicts, dates | markdown strings | YAML via yaml.dump() |
| hypothesis_parser | markdown string | parsed frontmatter + body | Raises ValueError on missing FM |
| schema_validator | markdown string, type | ValidationResult | Regex-based |
| pii_filter | DataFrame | DataFrame (copy) + column list | Logs warnings |
| plot_stats | arrays | StatResult, formatted strings | save_pvalues writes sidecar |
| plot_builders | DataFrame | (Figure, Axes) | Calls _ensure_theme() side effect |

### I/O Modules

| Module | Reads | Writes | Network | Idempotent |
|--------|-------|--------|---------|------------|
| obsidian_client | -- | Obsidian API | HTTPS | Partial (reads yes, writes no) |
| eda | CSV/Excel/Parquet | PNG plots | No | No (overwrites) |
| claim_exchange | notes/*.md | notes/*.md | No | Import: no unless overwrite |
| hypothesis_exchange | hypotheses/*.md | hypotheses/*.md | No | Import: no unless overwrite |
| pubmed | -- | -- | HTTPS | Yes (read-only API) |
| arxiv | -- | -- | HTTP | Yes (read-only API) |
| daemon_scheduler | vault dirs | -- | No | Yes (read-only scan) |
| decision_engine | vault + config | JSON to stdout | No | Yes |

### Implicit Contracts (enforced by convention, not code)

- [MED] Vault directory structure must exist before any module reads it
- [MED] Hypothesis YAML frontmatter field types (elo=number, matches=int) not enforced
- [MED] Wiki-link targets assumed to exist; broken links silently accepted
- [LOW] Hypothesis IDs assumed globally unique; no enforcement

---

## 3. Validation Gap Analysis

### [HIGH] Severity

| # | Location | Gap | Failure Scenario | Fix |
|---|----------|-----|------------------|-----|
| ~~1~~ | ~~obsidian_client.py:52-55~~ | ~~Missing API key defaults to empty string~~ | ~~Auth bypass~~ | **RESOLVED** -- lines 54-55 now raise `ObsidianAPIError` on empty key |
| 2 | plot_builders.py:518 | `.iloc[0]` without length check | IndexError on category with missing yerr values in build_bar_error | Check `len(subset) > 0` before indexing |
| 3 | R plot_builders.R build_heatmap() | No empty-matrix guard | `max(abs(mat), na.rm=TRUE)` returns -Inf on empty/all-NA matrix; breaks color scale | Validate matrix non-empty with finite values |

### [MED-HIGH] Severity

| # | Location | Gap | Failure Scenario | Fix |
|---|----------|-----|------------------|-----|
| 4 | daemon_scheduler.py:30-43 | Silent YAML parse failure returns `{}` | Malformed hypothesis FM silently treated as elo=0 | Log warning with filename |
| 5 | daemon_config.py:164 | Empty/truncated YAML returns default config | Corrupted config used without warning | Log filename + parse failure |
| 6 | vault_registry.py:71 | Unchecked `int()` on port | ValueError on non-numeric port string | try/except with default 27124 |
| 7 | federation_config.py:156,174,179 | Unchecked `float()` coercions | ValueError on "not_a_number" in min_elo | try/except with sensible defaults |
| 8 | R plot_builders.R build_volcano() | `-log10(y)` without y>0 check | NaN/Inf on zero or negative p-values | Validate y > 0 before transform |

### [MED] Severity

| # | Location | Gap | Failure Scenario | Fix |
|---|----------|-----|------------------|-----|
| 9 | pubmed.py:49, arxiv.py:65 | No socket.timeout catch on resp.read() | Unhandled timeout during XML parse | Wrap resp.read() in separate try |
| ~~10~~ | ~~decision_engine.py:401,445~~ | ~~`[0]` access without empty check~~ | ~~IndexError~~ | **RESOLVED** -- L401 guarded by `if tier3_gen:` (L399); L445 guarded by `raise ValueError` (L434) |
| 11 | plot_stats.py (volcano) | `np.log10()` without sign check | -Inf/NaN on p=0 | Validate pvalue in (0,1) |
| 12 | hypothesis_parser.py:154 | Off-by-one at insert_pos=0 | Doubled newlines at file start | Add `if insert_pos > 0` guard |
| 13 | rename-note.sh, backlinks.sh | User titles not regex-escaped | Titles with `.` or `*` produce wrong grep/sed matches | Use `grep -F` or escape |
| 14 | R stats_helpers.R format_pval() | No validation that p in [0,1] | Prints "p = 5.000" for invalid input | Clamp or error |

---

## 4. Bug-Risk Sweep

### Silent Fallbacks

| Location | Pattern | Risk |
|----------|---------|------|
| ~~obsidian_client.py:52~~ | ~~Missing API key -> empty string~~ | **RESOLVED** -- raises ObsidianAPIError |
| daemon_config.py:164 | Corrupt YAML -> default DaemonConfig | [MED-HIGH] |
| daemon_scheduler.py:42 | Bad frontmatter -> empty dict | [MED-HIGH] |
| decision_engine.py:111 | Unknown skill -> "sonnet" model | [MED] |
| R palettes.R | YAML parse failure -> hardcoded palette, no warning | [MED] |
| daemon.sh | Python config parsing errors -> defaults | [MED] |

### Broad Exception Handling

| Location | Pattern | Risk |
|----------|---------|------|
| session_capture.py:184-186 | `except Exception: pass` | [LOW] Session metadata silently lost |
| validate_write.py:109 | `except (JSONDecodeError, Exception)` bare return | [LOW] Validation silently bypassed |
| auto_commit.py:141-146 | `check=False` on git commit | [LOW] Failed commits not logged |

### Numeric Fragility

| Location | Pattern | Risk |
|----------|---------|------|
| elo.py:29 | 10^(elo_diff/400) -- no overflow clamp | [LOW] Inf on extreme ratings |
| R build_heatmap() | max(abs(empty_matrix)) = -Inf | [HIGH] Broken color scale |
| R build_volcano() | -log10(y <= 0) = NaN/Inf | [MED] |
| Python plot_stats volcano | np.log10(p=0) = -Inf | [MED] |

### State Leakage

| Location | Pattern | Risk |
|----------|---------|------|
| plot_theme.py:113 | `_PALETTES = load_palettes()` module-level mutable | [MED-LOW] Mutation persists across imports |
| plot_builders.py | `_ensure_theme()` modifies global matplotlib rcParams | [LOW] Expected side effect |

---

## 5. Reproducibility & Provenance Review

### Scorecard

| Criterion | Status | Evidence |
|-----------|--------|---------|
| Dependencies pinned | **PASS** | uv.lock with hashes; Python >=3.11; all versions locked |
| Randomness control | **PASS** | elo.py seeded; tests use `np.random.default_rng(42)`; experiment notes record seeds |
| Determinism | **WARN** | Unsorted `iterdir()` in daemon_scheduler.py -- L276,278 are order-independent (set + count), but pattern exists elsewhere in file |
| Provenance chain | **PASS** | Timestamps, source_vault, exported fields on all claims/hypotheses |
| Temporal stability | **WARN** | Live PubMed/arXiv API calls return different results over time; no response caching |
| Data versioning | **FAIL** | No checksums, no commit hash in output artifacts, no environment snapshot |
| Container option | **FAIL** | No Dockerfile or container definition |

### Key Gaps

- **No code version in outputs**: Cannot trace which commit generated a claim or hypothesis
- **No package version snapshot**: experiment notes record seeds but not numpy/pandas versions
- **Unsorted iterdir()**: daemon_scheduler.py -- L276,278 are order-independent (set + count only), but unsorted iteration pattern exists elsewhere in file
- **Live API dependency**: Literature searches are non-reproducible across time

---

## 6. Test Quality Assessment

### Coverage Summary

| Category | Metric | Status |
|----------|--------|--------|
| Overall Python coverage | 92% / 562 tests | Good |
| Python modules with tests | 20/20 | Complete |
| R modules with tests | 3/5 (60%) | Gap (plot_builders.R, plot_helpers.R untested) |
| Hook scripts with tests | 0/4 (0%) | Critical gap |
| Shell scripts with tests | 0/10 | Expected |
| Tests isolated from network | 100% | Excellent |
| Tests using fixed seeds | 90%+ | Excellent |
| Test execution time | ~6.4s | Fast |

### Missing High-Value Tests (ranked)

1. **Hook scripts** (704 LOC, 0% coverage) -- validate_write.py is critical for vault integrity
2. **Obsidian API error paths** -- no tests for HTTP 401/403/500, timeouts, malformed JSON
3. **R plot_builders.R** (8 functions, 0 tests) -- edge cases with empty data, NA, log of non-positive
4. **R plot_helpers.R** (3 functions, 0 tests)
5. **Daemon scheduler edge paths** (67 lines missing) -- observation/tension thresholds, health fixes
6. **Federation error paths** -- quarantine enforcement, trust level validation
7. **PubMed/arXiv error handling** -- malformed XML, timeouts, empty results
8. **EDA edge cases** -- empty DataFrame, all-NaN columns, non-numeric data
9. **End-to-end integration tests** -- none exist for full pipeline round-trips

### Assertion Strength

- **Strong**: elo (exact float comparisons with tolerance), claim_exchange (round-trip equality), daemon_scheduler (state machine assertions)
- **Weak**: obsidian_client (just `assert_called_once`, not payload), plot_builders (type check only, no content), eda (file exists but no format validation)

---

## 7. Dead Code & Technical Debt

### Dead/Unused Code

| Item | Location | Status | Effort |
|------|----------|--------|--------|
| decision_engine.py | 579 lines | Has tests but no production callers -- `/next` infrastructure not integrated | Small |
| claim_exchange.py | 233 lines | Tests only; federation feature not wired | Small |
| hypothesis_exchange.py | 246 lines | Tests only; federation feature not wired | Small |
| 3 unused batching config keys | daemon-config.yaml | tournament_threshold, verify_batch, validate_batch have no effect | Trivial |
| ~20 config.yaml keys | ops/config.yaml | dimensions, features, personality, processing -- never read by daemon | Small |

### Documentation Drift

| Item | Issue | Effort |
|------|-------|--------|
| README module table | Lists 14 modules; 5 undocumented (decision_engine, claim_exchange, hypothesis_exchange, federation_config, vault_registry) | Trivial |

### Tech Debt Patterns

| Pattern | Instances | Severity |
|---------|-----------|----------|
| Shell YAML parsing via sed (fragile) | 4 scripts | [MED] |
| daemon.sh JSON parsing repeated 4x (not DRY) | daemon.sh | [MED] |
| daemon.sh health gate nested 8 levels | daemon.sh | [MED] |
| BSD sed -i '' syntax (breaks GNU) | rename-note.sh | [MED] |
| Hardcoded directory paths in shell scripts | 6 scripts | [LOW] |

### Positive Findings

- Zero TODO/FIXME/HACK annotations
- Zero commented-out code blocks
- Zero unused imports
- Zero deprecated patterns (all modern Python/R)
- No circular dependencies
- Clean __init__.py exports matching actual modules

---

## 8. Prioritized Action Plan

### P0 -- Fix Now (silent correctness risks)

| # | Finding | Location | Effort | Status |
|---|---------|----------|--------|--------|
| 1 | `.iloc[0]` on potentially empty subset crashes EDA | plot_builders.py:518 | 1 line | OPEN |
| 2 | Empty matrix produces -Inf limits in heatmap | R plot_builders.R build_heatmap() | 3 lines | OPEN |
| 3 | `-log10(y<=0)` produces NaN/Inf in volcano plots | R plot_builders.R build_volcano() + Python plot_stats | 3 lines each | OPEN |
| ~~4~~ | ~~Missing API key silently defaults to empty string~~ | ~~obsidian_client.py:52-55~~ | -- | **RESOLVED** (guard already exists at L54-55) |
| 5 | Silent YAML parse failure returns empty dict for hypotheses | daemon_scheduler.py:30-43 | Add logging, 3 lines | OPEN |

### P1 -- Fix Soon (reliability risks, reproducibility gaps)

| # | Finding | Location | Effort |
|---|---------|----------|--------|
| 6 | Add `sorted()` to unsorted `iterdir()` calls (order-dependent sites only) | daemon_scheduler.py | 2 lines |
| 7 | Unchecked int/float coercions in config parsing | vault_registry:71, federation_config:156,174,179 | 10 lines |
| ~~8~~ | ~~Unsafe `[0]` access without empty check~~ | ~~decision_engine.py:401,445~~ | **RESOLVED** (both accesses already guarded) |
| 9 | Record code commit hash in exported claims/hypotheses | note_builder.py, claim_exchange.py | 20 lines |
| 10 | Add tests for hook scripts (validate_write.py first) | tests/ | 4-6 hours |
| 11 | Add tests for R plot_builders.R edge cases | R/tests/ | 2-3 hours |
| 12 | Escape user-provided titles in shell scripts | rename-note.sh, backlinks.sh | 5 lines each |
| 13 | Fix rename-note.sh BSD/GNU sed portability | rename-note.sh | 5 lines |

### P2 -- Fix Eventually (debt cleanup, nice-to-haves)

| # | Finding | Location | Effort |
|---|---------|----------|--------|
| 14 | Remove 3 unused batching config keys | daemon-config.yaml + daemon_config.py | Trivial |
| 15 | Update README module table (5 missing entries) | _code/README.md | Trivial |
| 16 | Decide on decision_engine.py: integrate or remove | decision_engine.py | Small |
| 17 | Decide on federation modules: wire up or mark experimental | claim/hypothesis_exchange | Small |
| 18 | Replace sed YAML parsing with Python/jq in shell scripts | 4 shell scripts | 1-2 hours |
| 19 | DRY up JSON parsing in daemon.sh (repeated 4x) | daemon.sh | 30 min |
| 20 | Log warnings when config/palette fallbacks are used silently | 4 locations | 30 min |
| 21 | Add Obsidian API error path tests (401/403/500/timeout) | tests/ | 2-3 hours |
| 22 | Add end-to-end integration tests | tests/ | 4-6 hours |
| 23 | Add Dockerfile for containerized reproducibility | project root | 1-2 hours |
| 24 | Add package version snapshot to experiment note builder | note_builder.py | 15 min |
| 25 | Consolidate hardcoded paths in shell scripts to central config | ops/scripts/ | 1 hour |

---

## Summary Metrics

| Metric | Value |
|--------|-------|
| Python test coverage | 92% (562 tests, 6.4s) |
| Circular dependencies | 0 |
| Unused imports | 0 |
| TODO/FIXME annotations | 0 |
| Dead code modules | 3 (federation + decision_engine -- tested but unwired) |
| P0 findings | 4 open, 1 resolved |
| P1 findings | 6 open, 1 resolved |
| P2 findings | 12 |
| Security notes added | 3 (shell injection, HTTP arxiv, SSL verify) |
| Reproducibility score | 7/10 (strong RNG control; missing code versioning + containers) |

The codebase is well-architected with clean separation of concerns and strong test discipline. The main risks are concentrated in: (a) silent fallbacks on malformed config/YAML, (b) numeric edge cases in plotting code, and (c) untested hook scripts that run on every user action. P0 items are all small fixes. The largest structural gap is the absence of code version tracking in output artifacts, which limits post-hoc reproducibility.

---

## Verification Log

**2026-02-23 -- Post-audit verification against current code:**

| Original Claim | Verdict | Detail |
|----------------|---------|--------|
| #1 obsidian_client auth bypass | INACCURATE | Lines 54-55 raise ObsidianAPIError on empty key -- guard already exists |
| #10 decision_engine `[0]` unguarded | INACCURATE | L401 inside `if tier3_gen:` (L399); L445 after `raise ValueError` (L434) |
| #6 iterdir L276,278 affects order | OVERSTATED | Those lines build a set and count -- order-independent. Pattern exists elsewhere. |
| R modules "3/7" | WRONG COUNT | 5 R modules exist, not 7. Correct ratio: 3/5 (60%) |
| All other claims | CONFIRMED | Verified against source at referenced line numbers |
