# Plan: Phase-Specific max_turns and Model Routing for Ralph

## Problem
Ralph subagents inherit the lead session's model and have no turn limits. This means:
1. All phases run at opus cost when the lead is opus (verify on opus is wasteful)
2. Runaway subagents can fill context without a circuit breaker
3. The daemon-config `models:` block is ignored by ralph

## Changes

### 1. Add phase budgets to daemon-config.yaml (~5 lines)

Add a `max_turns:` block under `models:` in `ops/daemon-config.yaml`:

```yaml
max_turns:
  create: 8
  verify: 8
  enrich: 8
  reflect: 15
  reweave: 15
  extract: 25
  cross_connect: 15
```

### 2. Update ralph SKILL.md Phase Configuration section (lines 66-83)

Replace the current "all phases use the same subagent configuration" block with a table that maps each phase to its model tier and max_turns budget. Reference daemon-config as the source of truth:

```
| Phase | Model (from daemon-config) | max_turns | Rationale |
|-------|---------------------------|-----------|-----------|
| extract | reduce -> sonnet | 25 | Large sources need many passes |
| create | (not in daemon-config) -> sonnet | 8 | Bounded: read task, write note |
| enrich | (not in daemon-config) -> sonnet | 8 | Bounded: read note, augment |
| reflect | reflect -> sonnet | 15 | Dual discovery + MOC update |
| reweave | reweave -> sonnet | 15 | Find + update older notes |
| verify | verify -> haiku | 8 | Schema + recite + review |
| cross-connect | (not in daemon-config) -> sonnet | 15 | Validate sibling links |
```

Add instruction: "Read `ops/daemon-config.yaml` models and max_turns blocks at Step 1 (queue read). Use these values when spawning subagents."

### 3. Update Agent call pattern in Step 4c (line 306-318)

Change from:
```
Agent(
  subagent_type = "general-purpose",
  prompt = {constructed prompt},
  description = "{current_phase}: {short target}"
)
```

To:
```
Agent(
  subagent_type = "general-purpose",
  prompt = {constructed prompt},
  description = "{current_phase}: {short target}",
  model = {model from daemon-config for this phase},
  max_turns = {max_turns from daemon-config for this phase}
)
```

### 4. Update parallel worker spawn in Step 6b (line 486-491)

Same pattern -- add `model` and `max_turns` to parallel worker Agent calls. Workers run all phases for a claim, so use the MOST GENEROUS budget from the phases they'll execute (claim pipeline = create+reflect+reweave+verify, so max_turns = 15 from reflect, model = sonnet since reflect/reweave need it).

### 5. Add model/max_turns fallback defaults

In Phase Configuration section, add: "If daemon-config is missing or unreadable, use defaults: model=sonnet for all phases except verify (haiku), max_turns per table above."

## Files Modified
1. `ops/daemon-config.yaml` -- add `max_turns:` block
2. `.claude/skills/ralph/SKILL.md` -- phase config table, Agent call patterns, daemon-config read instruction

## What Does NOT Change
- Queue schema (no changes)
- Subagent prompts (content unchanged, just Agent tool params added)
- Phase progression logic
- Error recovery
- Quality gates

## Unresolved questions

1. **Parallel worker budget**: Workers execute all 4 phases in sequence. Should `max_turns` be the sum of phase budgets (8+15+15+8=46) or the max single-phase budget (15)? The sum is safer since they genuinely need more turns, but 46 is high. Suggest: 30 as a compromise (generous but not unbounded).

2. **Create phase model**: daemon-config has no `create` entry. Default to `sonnet` (same as reduce) or add an explicit `create: sonnet` entry? Suggest: add it explicitly for completeness.
