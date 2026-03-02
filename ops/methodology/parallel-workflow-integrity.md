---
description: Guardrails for running parallel agent workflows without corrupting pipeline state or missing cross-connections
category: process-pattern
status: active
created: 2026-02-22
---

# Parallel Workflow Integrity

## Core Principle

> Reduce can fan out. Reflect must fan in.

Extraction is embarrassingly parallel -- each source is independent. Connection-finding is inherently sequential -- it needs to see the full graph. Split workflows at that boundary.

## Risks of Unserialized Parallel Work

| Risk | Mechanism | Consequence |
|------|-----------|-------------|
| Queue corruption | Two agents read/write queue.json simultaneously | Lost updates, double-processing |
| Duplicate claims | Independent agents extract same insight from different sources | Graph pollution, conflicting versions |
| Connection blindness | Agent A creates claim that Agent B should link to, but B never sees it | Orphaned knowledge, missed synthesis |
| Topic map race | Two agents append to same topic map concurrently | Overwritten entries |
| Phase skipping | Agent bypasses pipeline under parallel pressure | Unvalidated content in notes/ |

## Serialization Pattern

```
parallel:  /reduce source1, /reduce source2, /reduce source3
barrier:   wait for all reduce work to land
serial:    /reflect (sees all new claims at once)
serial:    /reweave (backward pass with full picture)
serial:    /verify (quality gate)
```

Use `/ralph` for this pattern -- it already manages fresh context per phase and serializes appropriately.

## Post-Batch Reconciliation

After any parallel work completes, run:

1. `/health` -- catch orphans, dangling links, schema violations
2. `/graph orphans` -- find unconnected claims
3. `/reflect` -- one pass to wire everything together

## Operational Rules

- **One topic map updater at a time** -- never let two agents touch the same topic map. Serialize updates or defer all to a single reflect pass.
- **Queue is not concurrent-safe** -- treat ops/queue/queue.json as single-writer. Use /ralph as the queue coordinator rather than launching manual parallel pipelines.
- **Dedup before commit** -- after parallel reduce, scan for title/description overlap before promoting to notes/.
- **Git as safety net** -- commit after each phase boundary. If something corrupts, you can revert to the last clean state.

## When to Parallelize

| Phase | Safe to parallelize? | Why |
|-------|---------------------|-----|
| /reduce | Yes | Each source is independent |
| /reflect | No | Needs full graph visibility |
| /reweave | No | Backward connections depend on current state |
| /verify | Yes (per-claim) | Validation is stateless |
| /tournament | No | Elo updates are sequential |
| /generate | Yes (per-goal) | Goals are independent |
| /review | Yes (per-hypothesis) | Reviews are independent |
