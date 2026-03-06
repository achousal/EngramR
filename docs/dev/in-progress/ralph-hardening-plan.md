# Ralph Pipeline Hardening Plan

Status: In Progress
Started: 2026-03-06

## Context

Systematic analysis of ralph's execution model identified 13 issues across 4 severity tiers. This plan organizes fixes into 4 implementation phases ordered by impact x likelihood.

## Issue Registry

| # | Issue | Severity | Tier |
|---|-------|----------|------|
| 1 | Parallel queue.json write collision | Silent data corruption | A |
| 2 | Split creates orphan queue entries without backlink | Silent data corruption | A |
| 3 | Enrich phantom target -- glob pattern too greedy | Silent data corruption | A |
| 4 | Phase gate deadlock (no failed state) | Stuck state | B |
| 5 | Turn budget exhaustion leaves partial state | Stuck state | B |
| 6 | Zero-claim extract advances to done | Stuck state | B |
| 7 | Parallel title rewrite in cross-connect | Graph integrity | C |
| 8 | Reflect links to sibling that later gets title-sharpened | Graph integrity | C |
| 9 | Topic map accumulates stale entries | Graph integrity | C |
| 10 | Skill Tool failure at iteration 7+ cascades | Operational fragility | D |
| 11 | Re-filter after every iteration is expensive | Operational fragility | D |
| 12 | No idempotency guard on phase re-execution | Operational fragility | D |
| 13 | Batch completion detection in serial mode is fragile | Operational fragility | D |

## Implementation Phases

### Phase 1: Task Status Model + Phase Gate Resilience (WS1 + WS4) -- DONE

Fixes: #4, #5, #6, #12, #13

**Python (`queue_query.py`):**
- `failed` status model: `fail_task()` marks tasks failed with reason + timestamp, preserves retry_count
- `retry_task()`: resets failed -> pending, increments retry_count, refuses at limit (8, matching daemon RetryConfig)
- `advance_task()`: auto-determines next phase from task type, handles done-marking with timestamps
- `get_alerts()`: surfaces failed tasks, identifies those at retry limit
- `get_batch_status()`: retroactive batch completion check
- `write_queue_atomic()`: temp-file-then-rename pattern
- Phase gate fix: `get_actionable()` only counts `pending` tasks -- `failed` tasks don't block
- New CLI subcommands: `fail`, `retry`, `alerts`, `advance`, `batches`

**SKILL.md:**
- `--unblock`/`--retry` arguments
- Step -1: handles unblock/retry before queue processing
- Step 3: overview shows failed count + retry-limit count
- Step 4a: idempotency guard (skip dispatch if task file section already filled)
- Step 4d: marks tasks `failed` when subagent returns without handoff AND empty task file
- Step 4e: uses CLI `advance` for phase progression; marks task `failed` if create note missing on disk
- Step 5: retroactive batch completion via `batches --check-complete`
- Gates 2/3/4 updated for failed-aware behavior; Gate 5 (idempotency) added
- Error Recovery: expanded with stuck pipeline / retry exhaustion guidance

**Other:**
- `repair_queue_targets.py`: handles `failed` status alongside `done`
- 25 new tests (42 total queue_query tests, 69 total queue-related tests)

---

### Phase 2: Queue Write Safety (WS2) -- DONE

Fixes: #1

**Problem:** In --parallel mode, worker subagents may write queue.json directly (line 557 says "update the queue entry to status done"). The lead ALSO writes queue.json. Race condition: last write wins.

**Changes applied:**
1. SKILL.md 6b: Removed "update the queue entry to status done" from worker prompt. Workers now report completion in RALPH HANDOFF block only. Explicit "Do NOT write to queue.json" instruction added.
2. SKILL.md 6c: Renamed to "Monitor Workers + Lead Queue Updates." Lead now handles ALL queue mutations after each worker returns -- advance via CLI on success, fail via CLI on error. Lead also runs post-create target sync and re-dispatches next phases.
3. Cross-connect note list now sourced from worker HANDOFF blocks (actual filenames) instead of queue targets (which may be stale after title sharpening). This also fixes #7.
4. Atomic write (`write_queue_atomic`) already shipped in Phase 1.

---

### Phase 3: Target Identity Integrity (WS3) -- DONE

Fixes: #3, #5 (partial, complements Phase 1), #7

**Problem:** Title drift across phases causes downstream operations to target wrong files. Multiple manifestations.

**Changes applied:**

1. **Enrich pre-dispatch (SKILL.md line 311):** Replaced `notes/**/[TARGET]*` prefix glob with exact match `notes/[TARGET].md` + case-insensitive fallback. Explicit "Never use prefix globs" instruction. Failure now marks task `failed` via CLI (not just "blocked") for consistency with Phase 1's error model.

2. **Post-phase target verification (parallel 6c):** Added post-reweave target sync to parallel path (6c already had post-create from Phase 2). Both serial (4e) and parallel (6c) now run target sync after create AND reweave.

3. **Parallel 6c handoff-sourced filenames:** Already completed in Phase 2 (line 639). No additional changes needed.

4. **Partial-fill inconsistency (4d):** Added step 5 to Evaluate Return: when handoff AND task file section are both present but report different note titles, log a warning with both titles. Handoff title takes precedence for target sync (it reflects the actual file on disk).

---

### Phase 4: Observability (WS5) -- PENDING

Fixes: #9, #10, #11

Lower priority. No data-loss risk.

1. **Topic map GC (#9):** New script `_code/scripts/maintenance/gc_topic_maps.py`. Diffs topic map wiki links against existing files. Reports dead links (does NOT auto-remove). Runnable manually or via `/health`.

2. **Skill Tool fallback caching (#10):** SKILL.md instruction: after first Skill Tool fallback, cache the SKILL.md content in the lead session. Re-inject from cache for remaining iterations instead of re-reading.

3. **Queue query caching (#11):** Deferred. Current CLI is fast enough for queues under 1000 entries.

---

## Priority Ranking (original analysis)

| Priority | Issue | Fix complexity |
|----------|-------|---------------|
| 1 | #4 Phase gate deadlock (no failed state) | Medium -- DONE |
| 2 | #1 Parallel queue.json write collision | Medium -- DONE |
| 3 | #5 Turn budget exhaustion leaves partial state | Low -- DONE |
| 4 | #12 No idempotency guard | Low -- DONE |
| 5 | #3 Enrich glob too greedy | Low -- DONE |
| 6 | #7 Parallel title rewrite in cross-connect | Low -- DONE |

## Design Decisions

- **Failed task retry model:** Auto-retryable with cap (8), matching daemon's `RetryConfig.max_per_task`. `--force` bypasses limit for manual intervention.
- **Queue mutation interface:** Unified in `queue_query.py` CLI (fail, retry, advance, batches subcommands). No separate scripts.
- **Topic map dead links:** Report only, no auto-removal. Preserves intentional forward-references.
