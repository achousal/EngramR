---
name: onboard
description: "Bootstrap EngramR integration for a lab. Hybrid scan + interview creates project notes, data inventory, research goals, and vault wiring. Triggers on /onboard, /onboard [path], /onboard --update."
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
  - WebFetch
  - Agent
argument-hint: "[lab-path] -- path to lab directory; --update for incremental mode"
---

## EXECUTE NOW

**Target: $ARGUMENTS**

You are the /onboard orchestrator. You run in main context -- natural conversation turns, no AskUserQuestion needed. Sub-skills handle computation in fork context; you handle all user interaction.

**Architecture:** This skill coordinates three fork sub-skills via the Agent tool (subagent_type: general-purpose). Each agent Reads its sub-skill file from `sub-skills/` and executes its instructions in isolation:
- `onboard-scan` -- filesystem scan, convention mining, institution lookup
- `onboard-generate` -- artifact creation (project notes, symlinks, data inventory)
- `onboard-verify` -- schema and link validation

Detailed instructions for each phase live in `reference/` files that sub-skill agents Read on demand.

---

## Phase 1: SETUP

### Parse arguments

| Input | Mode |
|-------|------|
| (empty) | Ask user for lab path in conversation |
| `~/projects/Lab_Name/` | Full onboard for that lab |
| `~/projects/` (root with multiple labs) | Multi-lab: detect subdirs |
| `--update` | Re-scan registered lab paths for new projects |

If no path provided, ask: "Which lab directory should I scan? Paste the path (e.g., ~/projects/My_Lab/)."

### Depth-first loading

If the user provides a multi-lab root, onboard ONE lab first. After completion, suggest the rest for later sessions. Comprehension before coverage -- the user's understanding compounds with each layer.

### Display roadmap

```
=== Onboarding Roadmap ===

4 phases, ~3-4 interactions from you:

  1. SCAN       Discover projects, mine conventions, look up institution.
                (Automatic -- no input needed.)

  2. REVIEW     Present findings for your correction.
                (Your main interaction -- confirm/adjust.)

  3. GENERATE   Create all vault artifacts after your approval.
                (One approval, then automatic.)

  4. SUMMARY    Verify and present results. Suggest /init.

=== Let's begin ===
```

---

## Phase 2: SCAN

Launch a scan agent using the Agent tool:

```
Agent(subagent_type: "general-purpose", model: "sonnet", description: "onboard scan")
Prompt: "Read and execute .claude/skills/onboard/sub-skills/onboard-scan.md with target: {lab-path}. Return the structured SCAN RESULTS output as specified in the sub-skill's Step 6."
```

Parse the structured output (Lab Profile, Infrastructure, Projects table, etc.).

---

## Phase 3: REVIEW (2-3 conversation turns)

Present scan results in focused stages. Each is a natural conversation turn.

### Turn 1: Institution and Infrastructure

Present the lab profile and infrastructure in a readable format:

```
=== Institution and Infrastructure ===

Lab Profile:
  PI:          {name}                    (from {source})
  Institution: {name}                    (confirmed)
  Departments: {list}
  Centers:     {list}

Lab Infrastructure:
  Compute:     {cluster / scheduler}
  Platforms:   {list}
  Facilities:  {list}

Also detected: {conventions summary}
```

Then ask:

"Does this look right? Correct any fields, add missing facilities or resources.

Also -- do you have a lab website URL? (optional -- helps fill in research themes, group members, and active projects)"

Wait for user response. Apply corrections.

### Turn 1b: Context Enrichment (automatic)

After user confirms Turn 1, enrich context before presenting projects. Goal: fill maximum institutional context. Two phases: parallel batch, then a sequential follow-up.

Read `reference/enrichment-agents.md` for the full agent prompt templates referenced below. Each agent invokes /learn via Skill tool, reads the filed inbox results, and returns structured output.

#### Phase A (parallel)

Launch all available enrichment steps simultaneously via a single message with multiple tool calls.

- **A1. Lab profile** (always runs; URL optional): Launch agent using A1 template from `reference/enrichment-agents.md`. Does WebFetch of lab URL (if provided) + /learn for broader lab context. Substitute `{PI Name}`, `{Institution Name}`, `{lab_website_url}`.
- **A2. Departments** (if Departments or Centers show "--"): Launch agent using A2 template from `reference/enrichment-agents.md`. Substitute `{PI Name}` and `{Institution Name}`.
- **A3. Institutional resources** (if scan produced thin infrastructure): Launch agent using A3 template from `reference/enrichment-agents.md`. Substitute `{Institution Name}` and `{domain}`.

#### Phase B (sequential, after Phase A)

- **B1. Department-specific resources** (only if A2 returned departments): Parse department names from A2 output. Launch agent(s) using B1 template from `reference/enrichment-agents.md`. Limit to 2 most relevant departments. Run in parallel if multiple.

#### Merge and Present

Merge enrichment results into scan data. Deduplicate against filesystem-detected infrastructure.

```
=== Context Enrichment ===

{if lab website}: Lab website: {N} research themes, {N} group members, {N} projects found.
{if departments}: Departments: {list with types}. Centers: {list}.
{if external}: External affiliations: {list}.
{if institutional}: Infrastructure: {N} compute, {N} core facilities, {N} platforms, {N} shared resources.
{if dept-specific}: Department resources: {summary per department}.

Enriched fields will inform project registration and goal creation.
```

Proceed to Turn 2.

### Turn 2: Projects

Present the project table:

```
=== {Lab Name} ({N} projects) ===

| # | Project | Status | Domain | Languages | Data Layers | Data Access | Research Q |
|---|---------|--------|--------|-----------|-------------|-------------|------------|
{rows from scan}

Fields marked -- could not be auto-detected.
```

Then ask: "Anything to adjust? You can correct fields, fill in Data Access, or deselect projects."

Wait for user response. Apply corrections.

### Turn 2b: Data Platform Enrichment (automatic)

After user confirms projects, collect all unique data platforms detected across projects (from Data Layers and scan conventions). Examples: UK Biobank, SomaScan, REDCap, Quanterix SIMOA, BioMe Biobank, MSD V-PLEX, etc.

If platforms were detected, launch enrichment agents in parallel using the C1 template from `reference/enrichment-agents.md`. Limit to 4 most prominent platforms to avoid excessive lookups.

Merge results into `_research/data-inventory.md` entries during artifact generation.

Present brief summary:

```
=== Data Platform Enrichment ===

{per platform}: {platform name}: {N} data fields, access via {method}, {N} published studies found.

Platform details will populate data-inventory.md entries.
```

Proceed to Turn 3.

### Turn 3: Cross-lab connections (multi-lab only)

If onboarding multiple labs, present detected cross-lab connections after all labs reviewed.

Ask: "Any connections I missed between labs?"

### Turn 4: Strategy (optional)

Ask: "Anything else I should know? Research directions not captured by these projects, upcoming datasets, or collaborations? (Skip if nothing.)"

If user provides additional context, incorporate into goal creation.

---

## Phase 4: GENERATE

Present the artifact list:

```
Ready to create:
- projects/{lab}/{tag}.md (per NEW project)
- projects/{lab}/_index.md (lab entity)
- _dev/{tag} symlinks
- _research/goals/{slug}.md (if new directions)
- projects/_index.md updates
- _research/data-inventory.md entries
- self/goals.md thread updates

Proceed?
```

Wait for user approval.

**On approval:** Write the corrected scan data to a temp file, then launch a generation agent:

```
Agent(subagent_type: "general-purpose", model: "sonnet", description: "onboard generate")
Prompt: "Read and execute .claude/skills/onboard/sub-skills/onboard-generate.md with target: {temp-file-path}. Return the structured ARTIFACTS CREATED output as specified in the sub-skill's Step 5."
```

Parse the output (files created, modified, symlinks).

Then launch a verification agent:

```
Agent(subagent_type: "general-purpose", model: "haiku", description: "onboard verify")
Prompt: "Read and execute .claude/skills/onboard/sub-skills/onboard-verify.md. Return the structured VERIFICATION REPORT as specified in the sub-skill's Step 4."
```

---

## Phase 5: SUMMARY

Present summary:

```
=== /onboard Summary ===

Lab: {name} ({path})
Institution: {name or "none"}
Projects registered: {N}
{list with tags}

Data inventory entries: {N}
Research goals created: {N}
Symlinks created: {N}

=== Quick Orientation ===

Your vault now has {N} projects. Here is how to navigate:

  projects/{lab}/_index.md     Lab profile with project links
  _research/data-inventory.md  Data coverage matrix
  _research/goals/             Research goals (seeded by /init)
  notes/                       Knowledge claims (populated by /init)

The knowledge graph is currently empty. /init will create
your first claims in four layers:

  Orientation   -- what you study
  Methodology   -- how you study it
  Confounders   -- what could fool you
  Inversions    -- what would prove you wrong

=== What's Next ===

>> /init                                          [START HERE]
   Seeds all four claim layers for your research goals.

Then: /literature, /reduce, /reflect, /research
=== End Summary ===
```

If verification found issues, report them inline.

---

## Mode: --update

For incremental mode:
1. Read registered project paths from `projects/*/*.md` frontmatter
2. Re-scan each lab root for new subdirectories
3. Skip review of existing projects
4. Only present NEW discoveries
5. Follow same generate + verify flow for new projects only

## Mode: Handoff

If `--handoff` was included in arguments, append RALPH HANDOFF block after the summary (see reference/conventions.md for format).

---

## Error Handling

| Error | Behavior |
|-------|----------|
| Lab path does not exist | Report error, ask for correct path |
| No projects detected | Report indicators checked, ask if path is correct |
| Sub-skill invocation fails | Report error, offer to retry or proceed manually |
| User wants to skip a phase | Respect the skip, note it in summary |

---

## Skill Graph

Invoked by: user (standalone), /ralph (delegation)
Invokes: onboard-scan, onboard-generate, onboard-verify (via Agent tool); /learn (via onboard-scan agent)
Suggests next: /init (primary), /literature, /reduce, /reflect
Reads: projects/, _research/data-inventory.md, _research/goals/, self/goals.md, ops/reminders.md, ops/config.yaml, filesystem
Writes: projects/, _research/data-inventory.md, _research/goals/, self/goals.md, ops/reminders.md, projects/_index.md, _dev/ symlinks, ops/institutions/
