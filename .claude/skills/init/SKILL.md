---
name: init
description: "Guided knowledge seeding for new vaults or cycle transitions. Seeds orientation claims, methodological foundations, and assumption inversions. Cycle mode generates transition summaries and refreshes inversions."
version: "2.0"
generated_from: "arscontexta-v1.6"
user-invocable: true
context: main
model: sonnet
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Skill
  - Agent
argument-hint: "[goal-name] | --cycle | --handoff"
---

## EXECUTE NOW

**Target: $ARGUMENTS**

You are the /init orchestrator. You run in main context -- natural conversation turns, no AskUserQuestion needed. Sub-skills handle computation in fork context; you handle all user interaction.

**Architecture:** This skill coordinates three fork sub-skills via the Agent tool (subagent_type: general-purpose). Each agent Reads its sub-skill file from `sub-skills/` and executes its instructions in isolation:
- `init-orient` -- reads vault state, produces structured summary
- `init-generate` -- generates all claims (orientation, methodology, confounders, inversions)
- `init-wire` -- wires claims into topic maps, project bridges, goal updates

Detailed instructions for each phase live in `reference/` files that sub-skill agents Read on demand.

---

## Mode Selection

Parse `$ARGUMENTS`:

| Input | Mode |
|-------|------|
| (empty) | Seed mode -- interactive goal selection, full pipeline |
| `{goal-name}` | Seed mode -- direct seeding for named goal |
| `--cycle` | Cycle mode -- read `reference/cycle-mode.md` and follow those instructions |
| `--handoff` (appended) | Any mode + RALPH HANDOFF at end |

If `--cycle`, read `.claude/skills/init/reference/cycle-mode.md` and follow its instructions directly. The remainder of this file covers seed mode only.

---

## Phase 0: ORIENT

Launch an orient agent using the Agent tool:

```
Agent(subagent_type: "general-purpose", model: "haiku", description: "init orient")
Prompt: "Read and execute .claude/skills/init/sub-skills/init-orient.md. Return the structured ORIENT RESULTS output as specified in the sub-skill."
```

Parse the structured output: CLAIM_COUNT, goals list, vault state, VAULT_INFORMED flag.

### Re-init detection

If CLAIM_COUNT > 0, tell the user:

```
Your vault already has {CLAIM_COUNT} claims. /init is designed for early-stage seeding.

Options:
1. Seed a new goal -- add foundation claims for a goal that lacks seeding
2. Full re-seed -- generate all claim types from scratch (existing claims preserved)
3. Cancel -- exit without changes
```

Wait for user response. If cancel, stop.

### Infrastructure check

If `_research/goals/`, `self/goals.md`, or `projects/_index.md` are missing, warn:

```
Missing infrastructure: {list}
Recommendation: Run /onboard first, then return to /init.
Continue anyway?
```

Wait for response.

---

## Phase 1: GOAL + QUESTIONS (2-3 conversation turns)

### Turn 1: Goal review and selection

If a goal name was provided as argument, look it up and proceed to Turn 2.

Otherwise, present available goals from the orient output as **suggestions the user owns**:

```
=== Research Goals ===

These were created during onboarding. They are suggestions -- you own them.

{numbered list, each with title and one-line scope from the goal file's Objective}

You can:
- Select a goal to seed (by number or name)
- Edit a goal -- change its title, scope, or framing before seeding
- Add a new goal -- describe a research direction not listed here
- Remove a goal -- if it no longer fits your program

Which goal would you like to work with first?
```

Wait for user response.

**If user edits a goal:** Apply changes to the goal file in `_research/goals/` and update `self/goals.md` before proceeding. Re-present the edited goal for confirmation.

**If user adds a new goal:** Create a new goal file following `_code/templates/research-goal.md`, update `self/goals.md`, then proceed with seeding it.

**If user removes a goal:** Confirm removal. Delete the goal file and remove its entry from `self/goals.md`.

**Depth-first:** If user selects multiple goals, seed ONE first. After completion, suggest the rest for follow-up sessions.

### Turn 2: Core questions

For the selected goal, generate 3-5 suggested core questions based on the goal's scope, linked projects, and any available vault context (data inventory, literature, project CLAUDE.md files). Then present them as editable suggestions:

```
For the goal "{goal title}":

Here are suggested core questions based on your projects and scope:

1. "{suggested question 1}"
2. "{suggested question 2}"
3. "{suggested question 3}"
{4-5 if warranted}

You can:
- Approve these as-is
- Edit any question (by number)
- Add your own questions
- Remove questions that miss the mark
- Replace all with your own
```

Wait for user response. Parse into individual questions.

**Quality bar for suggestions:** Each question should be specific enough to generate falsifiable hypotheses. Prefer "Does X predict Y in population Z?" over "What is the role of X?" Ground suggestions in the actual data and methods available in the linked projects.

---

## Phase 2: DEMO CLAIM (2 turns) -- KEY UX IMPROVEMENT

The user's first generative act. Building one thing teaches more than reviewing thirty.

### Turn 1: Suggest and compose together

Take the user's FIRST core question. Generate a suggested claim from it -- transform the question into a propositional statement grounded in the goal's scope and available data. Then present:

```
Let's turn your first question into a claim.

Question: "{first core question}"

A claim is a prose proposition -- a complete thought someone could agree or disagree with.
Test: "This claim argues that [title]" must work as a sentence.

Here is a suggested claim:

  Title:       "{suggested propositional title}"
  Description: "{suggested description, ~150 chars}"
  Confidence:  {suggested level}

You can:
- Approve as-is
- Edit any field
- Replace with your own claim entirely
```

Wait for user response. Parse title, description, confidence.

**Quality bar for suggestion:** The title must be a falsifiable proposition, not a topic label. The description must add new information beyond the title. Ground the suggestion in what the user's projects can actually test.

### Turn 2: Review and write

Construct the full claim with YAML frontmatter and body. Present:

```
Here is your first claim:

File: notes/{sanitized-title}.md
Title: {title}
  (Test: "This claim argues that {title}" -- reads as a sentence)
Description: {description}
Confidence: {confidence}

---
description: "{description}"
type: claim
role: orientation
confidence: {confidence}
source_class: synthesis
verified_by: agent
created: {today}
---

{2-3 sentence body based on user's framing}

---

Topics:
- [[{relevant-topic-map}]]

Approve, edit, or skip?
```

Wait for response.

**If approved:** Write to `notes/{sanitized-title}.md`. This is the demo claim.

**If edit:** Apply edits, re-present.

**If skip:** Proceed without demo claim. No penalty.

---

## Phase 3: BATCH GENERATION (fork)

Write input data to a temp file:
- SELECTED_GOALS
- CORE_QUESTIONS (all of them)
- DEMO_CLAIM (if approved -- counts as first orientation claim)
- VAULT_STATE (from orient output)
- VAULT_INFORMED flag

Launch a generation agent:

```
Agent(subagent_type: "general-purpose", model: "sonnet", description: "init generate")
Prompt: "Read and execute .claude/skills/init/sub-skills/init-generate.md with target: {temp-file-path}. Return the structured GENERATED CLAIMS output as specified in the sub-skill."
```

Parse the structured output: claims grouped by role with titles and filenames.

---

## Phase 4: REVIEW (1-2 conversation turns)

Present claims grouped by role for review:

```
=== Generated Claims ===

Orientation ({N}):
{numbered list of titles with one-line descriptions}

Methodology ({N}):
{numbered list}

Confounders ({N}):
{numbered list, each noting which orientation claim it threatens}

Inversions ({N}):
{numbered list, each noting which orientation claim it challenges}

Total: {N} claims

Review each group. You can:
- Approve all
- Remove specific claims by number
- Edit a claim's title or description
- Request additional claims for a category
```

Wait for user response. Apply any edits/removals.

If user removes claims, note which ones. If user requests additions, note those for a follow-up generation (or handle inline if simple).

---

## Phase 5: WIRE (fork)

Write approved claims list to a temp file. Launch a wiring agent:

```
Agent(subagent_type: "general-purpose", model: "sonnet", description: "init wire")
Prompt: "Read and execute .claude/skills/init/sub-skills/init-wire.md with target: {temp-file-path}. Return the structured WIRING SUMMARY output as specified in the sub-skill."
```

Parse the wiring summary.

---

## Phase 6: SUMMARY

Present final summary:

```
=== /init Seeding Summary ===

Goal seeded: {name}

Claims created: {total}
  Orientation:    {count}
  Methodology:    {count}
  Confounders:    {count}
  Data realities: {count}
  Inversions:     {count}

Topic maps: {created count} created, {updated count} updated
Project bridges: {count} wired

Graph health:
- Orphan claims: {count} (should be 0)
- Dangling links: {count} (should be 0)

Your knowledge graph now has a four-layer foundation.
Each orientation claim has methodology context, confounders
that challenge it, and inversions that would falsify it.

=== What's Next ===

/literature -- search for papers supporting or challenging these claims
/generate  -- produce hypotheses building on this foundation
/reflect   -- find connections between new and existing claims
=== End Summary ===
```

If other goals remain unseeded, suggest: "You have {N} other goals. Run `/init {goal-name}` to seed them."

---

## Handoff Mode

If `--handoff` was included, append RALPH HANDOFF block after the summary:

```
=== RALPH HANDOFF: init ===
Target: {arguments}
Mode: seed

Work Done:
- {summary of actions taken}

Files Modified:
- {list}

Claims Created:
- {list of claim titles}

Learnings:
- [Friction]: {any} | NONE
- [Surprise]: {any} | NONE
- [Methodology]: {any} | NONE

Queue Updates:
- Suggest: {follow-up actions}
=== END HANDOFF ===
```

---

## Error Handling

| Error | Behavior |
|-------|----------|
| No goals exist | Suggest /research to create a goal, or offer to create inline |
| Re-init on populated vault | Soft detection + user choice (Phase 0) |
| Missing infrastructure | Warn + recommend /onboard (Phase 0) |
| Sub-skill fails | Report error, offer to retry or proceed manually |
| Duplicate claim title | Report to user, ask for rephrasing |
| validate_write hook rejects | Parse error, fix claim, retry once |

---

## Skill Graph

Invoked by: user (standalone), /ralph (delegation), /onboard (suggested next step)
Prerequisite: /onboard (creates research goals and project infrastructure)
Invokes: init-orient, init-generate, init-wire (via Agent tool); /research (if user needs a new goal)
Suggests next: /literature, /generate, /reflect
Reads: self/, _research/goals/, _research/meta-reviews/, notes/, projects/
Writes: notes/ (claims), _research/cycles/ (cycle summaries), self/goals.md, projects/ (linked_goals wiring)
