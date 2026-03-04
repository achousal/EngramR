---
name: enrich
description: Integrate new evidence into existing claims. Adds source material to target notes with proper citation, upgrades YAML provenance fields, and signals downstream actions (title-sharpen, split, merge). Always dispatched by ralph pipeline, never called interactively.
user-invocable: false
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
context: fork
---

## Runtime Configuration (Step 0 -- before any processing)

Read these files to configure behavior:

1. **`ops/config.yaml`** -- processing depth, pipeline chaining
   - `processing.depth`: deep | standard | quick
   - `processing.chaining`: manual | suggested | automatic

**Processing depth adaptation:**

| Depth | Enrich Behavior |
|-------|----------------|
| deep | Full integration. Read all source lines. Integrate as prose with full mechanistic context. Evaluate YAML upgrades across all provenance fields. Assess post_enrich_action thoroughly. |
| standard | Balanced integration. Read source lines. Integrate key evidence as prose. Upgrade YAML where clearly warranted. Assess post_enrich_action. |
| quick | Minimal integration. Add core evidence sentence with citation. Upgrade source_class if obvious. Skip post_enrich_action assessment (set NONE). |

## Quarantine Guard

Before processing the target note, check its frontmatter for `quarantine: true`. Quarantined notes are federation imports that have not been human-verified and must not participate in graph-building operations.

**Action:** If the target note has `quarantine: true` in its YAML frontmatter, skip it with a log message: "Skipping quarantined note [[note-title]] -- awaiting human review." Do NOT enrich quarantined notes. Report skip in handoff.

## EXECUTE NOW

**Target: $ARGUMENTS**

Parse immediately:
- The task file path is provided by ralph in the prompt
- If arguments contain `--handoff`: output RALPH HANDOFF block at end

**Execute these steps:**

### Step 1: Read Task File

Read the task file at the path provided. Parse frontmatter fields:
- `target_note`: wiki-link to the claim to enrich
- `addition`: summary of what to add
- `source_task`: literature archive filename (without extension)
- `source_lines`: line numbers to read from the literature archive

### Step 2: Locate Target Note

Use Glob to find the target note in `notes/`:

```bash
# Extract note name from wiki-link brackets
Glob notes/**/[TARGET_NAME]*.md
```

**GATE:** If the target note does not exist on disk, STOP. Do not fabricate content. Output in handoff: `"blocked": "target note does not exist on disk"`. This is a hard failure.

### Step 3: Read Source Lines

Read the literature archive file at `_research/literature/{source_task}.md`. Navigate to the specific `source_lines` referenced in the task file. These lines contain the actual evidence to integrate.

**GATE:** If the archive file does not exist or source_lines are not found, STOP. Output in handoff: `"blocked": "source archive or lines not found"`.

### Step 4: Read Target Note

Read the target note fully. Understand:
- Current claim (title as proposition)
- Current body text and reasoning
- Current YAML frontmatter (confidence, source_class, source, verified_by)
- Current wiki links and connections

### Step 5: Integrate Addition into Target Note

Add the new evidence as **prose** integrated into the body text. Rules:
- Write as a new paragraph or extend an existing paragraph where the evidence fits naturally
- Cite the source with an inline wiki link: `[[source-task-name]]`
- Include author-year citation in the prose (e.g., "Cipollini 2019")
- Preserve ALL existing content unchanged -- add, do not replace
- The integrated text must use ONLY content from the source_lines read in Step 3. NEVER fabricate evidence from training knowledge
- The addition must read as coherent prose continuous with the existing body, not as a list append or footnote

### Step 6: Evaluate YAML Upgrades

Check whether the new evidence warrants YAML field changes:

| Field | Upgrade When | Example |
|-------|-------------|---------|
| `confidence` | Published evidence upgrades from speculative/preliminary | speculative -> supported |
| `source_class` | Published source upgrades from synthesis/hypothesis | synthesis -> published |
| `source` | Add source wiki-link if field is empty or append if multiple | `"[[source-note]]"` |

**NEVER touch `verified_by`, `verified_who`, or `verified_date`.** These are human-verification fields only.

**YAML safety:** Always double-quote all string values in YAML frontmatter.

### Step 7: Assess post_enrich_action

Evaluate the target note AFTER integration. Signal one of:

| Action | Condition | Detail to Record |
|--------|-----------|-----------------|
| `NONE` | Claim remains focused and well-titled after enrichment | -- |
| `title-sharpen` | The title is now too vague for the enriched content | Suggested new title |
| `split-recommended` | The note now covers multiple distinct claims | Which claims to split into |
| `merge-candidate` | The enriched note substantially overlaps another note | Which note it overlaps with |

Record the assessment and detail in the task file.

### Step 8: Update Task File

Write the `## Enrich` section of the task file with:
- Date completed
- Changes made to the target note (numbered list):
  - Content added (summary of what was integrated)
  - YAML fields updated (or "NONE")
  - Source lines used
- post_enrich_action assessment
- Confirmation: "No new files created; edit confined to target claim only."

### Step 9: Handoff (if --handoff flag)

If `--handoff` is in arguments, output the RALPH HANDOFF block.

**START NOW.** Reference below explains quality gates and output format -- use to guide, not as output.

---

# Enrich

Integrate new evidence from literature into existing claims. The enrichment pipeline adds published findings to claims that were originally created from a different source, strengthening evidence chains and upgrading provenance.

## Philosophy

**Claims grow through evidence accumulation, not just creation.**

When /reduce extracts claims from source A, and source B contains evidence that strengthens or contextualizes an existing claim, the enrichment pipeline adds that evidence to the existing claim rather than creating a duplicate. This prevents claim proliferation while building richer, better-grounded notes.

Enrichment is surgical: one target note, one source, specific lines. The skill reads actual source text and integrates it as prose. No fabrication, no inference beyond what the source lines state.

## Quality Gates

### Gate 1: Target Existence

The target note must exist on disk. Ralph pre-validates this, but the skill double-checks. Phantom targets (created by reduce-phase hallucination) are caught here.

### Gate 2: Source Fidelity

Only content from the specified source_lines may be integrated. The skill reads the actual archive lines -- model training knowledge must NEVER substitute for missing source content. Zero enrichment from unreadable source lines is correct; fabricated enrichment is a provenance failure.

### Gate 3: No New Files

Enrichment modifies exactly two files: the target note and the task file. No new claims are created. If the evidence warrants a new claim, that is a /reduce task, not an /enrich task.

### Gate 4: Note Coherence

After integration, the claim must still read as a single focused piece. If adding evidence makes the note incoherent or multi-topic, signal `split-recommended` rather than forcing coherence.

### Gate 5: Wiki-Link Safety

Before adding any new wiki link, verify the link target exists on disk:

```bash
Glob notes/**/[LINK_TARGET]*.md
```

Do NOT create wiki links to non-existent files.

### Gate 6: YAML Safety

All string values in YAML frontmatter must be double-quoted. Unquoted colons, commas, and brackets break parsing.

---

## Output Format

The primary output is the updated target note and task file. The skill does not produce a standalone report -- the task file's ## Enrich section IS the record.

---

## Handoff Mode (--handoff flag)

When invoked with `--handoff`, output this structured format at the END of the session. This enables /ralph to parse results and update the task queue.

**Detection:** Check if `$ARGUMENTS` contains `--handoff`. If yes, append this block after completing the workflow.

**Handoff format:**

```
=== RALPH HANDOFF: enrich ===
Target: [[note name]]

Work Done:
- Content added: [summary of what was integrated]
- YAML updated: [fields changed] | NONE
- post_enrich_action: NONE | title-sharpen | split-recommended | merge-candidate

Files Modified:
- notes/[target].md
- ops/queue/[task file].md (enrich section)

Learnings:
- [Friction]: [description] | NONE
- [Surprise]: [description] | NONE
- [Methodology]: [description] | NONE
- [Process gap]: [description] | NONE

Queue Updates:
- Advance phase: enrich -> reflect
=== END HANDOFF ===
```

### Task File Update

After completing the workflow, update the `## Enrich` section of the task file with the changes-made summary. The downstream phases (reflect, reweave, verify) each have their own sections to fill.

**Critical:** The handoff block is OUTPUT, not a replacement for the workflow. Do the full enrich workflow first, update task file, then format results as handoff.

## Pipeline Chaining

After enrichment completes, the next phase is **reflect** per the enrichment phase_order (enrich -> reflect -> reweave -> verify).

Output the next step based on `ops/config.yaml` pipeline.chaining mode:

- **manual:** Output "Next: /reflect [[note]]" -- user decides when to proceed
- **suggested:** Output next step AND advance task queue entry to `current_phase: "reflect"`
- **automatic:** Queue entry advanced and reflect proceeds immediately

---

## Critical Constraints

**Never:**
- Create new claim files -- enrichment modifies existing claims only
- Fabricate evidence from training knowledge -- only source_lines content
- Touch verified_by, verified_who, or verified_date fields
- Add wiki links to non-existent files
- Replace or delete existing content in the target note
- Run phases beyond enrich (do NOT run reflect, reweave, or verify)

**Always:**
- Read actual source lines from the literature archive
- Preserve all existing body text and connections
- Double-quote YAML string values
- Record changes in the task file ## Enrich section
- Verify link targets exist before adding wiki links
- Signal post_enrich_action for downstream processing
