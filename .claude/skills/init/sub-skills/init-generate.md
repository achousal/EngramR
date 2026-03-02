---
name: init-generate
description: "Generate all claims for /init seeding -- orientation, methodology, confounders, inversions. Internal sub-skill -- not user-invocable."
version: "1.0"
user-invocable: false
context: fork
model: sonnet
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
argument-hint: "{data-file-path} -- path to temp file with core questions, demo claim, and vault state"
---

## EXECUTE NOW

**Target: $ARGUMENTS**

Generate all claims for /init knowledge seeding. This is a computational sub-skill invoked by the /init orchestrator after the user has provided core questions and approved a demo claim.

### Step 1: Read Input

Read the input data file from $ARGUMENTS. It contains:
- SELECTED_GOALS: list of goals to seed
- CORE_QUESTIONS: per-goal list of 3-5 scientific questions
- DEMO_CLAIM: the user's demo claim (if approved) -- this counts as the first orientation claim
- VAULT_STATE: structured summary from init-orient (lab conventions, data inventory, code tools)
- VAULT_INFORMED: true/false

### Step 2: Read Reference Instructions

```
Read .claude/skills/init/reference/claim-conventions.md
Read .claude/skills/init/reference/orientation-phase.md
Read .claude/skills/init/reference/methodology-phase.md
Read .claude/skills/init/reference/inversion-phase.md
```

### Step 3: Generate Orientation Claims (Phase 2)

For each goal, for each core question NOT covered by the demo claim:
- Generate ONE orientation claim per the reference instructions
- Follow all claim conventions (prose-as-title, YAML schema, body structure)
- Verify wiki-link targets exist before including them
- Write each claim to `notes/{sanitized-title}.md`

Track as ORIENTATION_CLAIMS.

### Step 4: Generate Methodology Claims (Phase 3)

Follow `reference/methodology-phase.md`:

**3a. Analytical methods** -- 2-4 claims from vault state or inferred from orientation claims
**3b. Confounders** -- 1-2 per orientation claim, using vault data or generic confounders
**3c. Data realities** -- 2-3 claims from data inventory or generic constraints

Write each claim to `notes/{sanitized-title}.md`.

### Step 5: Generate Inversion Claims (Phase 4)

Follow `reference/inversion-phase.md`:

For each orientation claim, generate ONE inversion -- a proposition that, if true, falsifies the parent claim.

Each inversion MUST wiki-link to its parent orientation claim.

Write each claim to `notes/{sanitized-title}.md`.

### Step 6: Output Claim List

```markdown
## CLAIMS GENERATED

### Orientation ({count})
{numbered list: title | filename | goal}

### Methodology ({count})
{numbered list: title | filename}

### Confounders ({count})
{numbered list: title | filename | parent orientation claim}

### Data Realities ({count})
{numbered list: title | filename}

### Inversions ({count})
{numbered list: title | filename | parent orientation claim}

### Total: {count}

### Topic Maps Referenced
{list of topic map names referenced in Topics: footers}

### Errors
{any write failures, hook rejections, or link issues encountered}
```

This output is consumed by the /init orchestrator for grouped review presentation.
