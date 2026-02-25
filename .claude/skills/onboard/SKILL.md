---
name: onboard
description: "Bootstrap EngramR integration for a lab. Hybrid scan + interview creates project notes, data inventory, research goals, and vault wiring. Triggers on /onboard, /onboard [path], /onboard --update."
version: "1.0"
generated_from: "arscontexta-v1.6"
user-invocable: true
context: fork
model: sonnet
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
argument-hint: "[lab-path] \u2014 path to lab directory; --update for incremental mode"
---

## EXECUTE NOW

**Target: $ARGUMENTS**

Bootstrap or update EngramR vault integration for a research lab. Scan filesystem, interview user, generate vault artifacts.

### Step 0: Read Vocabulary and Vault State

Read `ops/derivation-manifest.md` (or fall back to `ops/derivation.md`) for domain vocabulary mapping. Then read current vault state:

1. `projects/_index.md` -- existing registered projects
2. `_research/data-inventory.md` -- existing data entries (read Summary Table only, first 60 lines)
3. `self/goals.md` -- current Active Threads and Research Goals
4. `ops/reminders.md` -- current reminders

Collect the set of already-registered project tags from `projects/_index.md` wiki-links and from `projects/` subdirectory filenames:

```bash
ls projects/*/*.md 2>/dev/null | xargs basename -a | sed 's/\.md$//'
```

Store this as REGISTERED_TAGS for Phase 3 diffing.

**Note:** All relative paths in Bash commands are relative to the vault root (repository root).

**START NOW.** Parse arguments and begin onboarding.

---

## Step 1: Argument Parse and Mode Selection

Parse `$ARGUMENTS` to determine mode:

| Input | Mode | Behavior |
|-------|------|----------|
| (empty) | interactive | Ask user for lab path, then full onboard |
| `~/projects/Lab_Name/` | full | Scan directory, full onboard for that lab |
| `--update` | incremental | Re-scan all registered lab paths for new projects |
| `~/projects/Lab_Name/NewProject/` | single-add | Add one project to existing lab |
| `--handoff` (appended) | any + handoff | Run chosen mode, output RALPH HANDOFF at end |

### Mode: interactive
Ask user:
```
Which lab directory should I scan for projects?
Example: ~/projects/Elahi_Lab/
```

### Mode: incremental (`--update`)
Read all registered project notes from `projects/*/*.md`. Extract unique `project_path` values from frontmatter. Derive lab root directories (parent of each project_path). Re-scan each lab root for new subdirectories not yet registered. Skip Phase 4 lab-level interview. Only ask per-project questions for NEW discoveries.

### Mode: single-add
If the path points to a single project directory (contains .git/, CLAUDE.md, data/, analysis/, *.R, *.py, or similar), treat it as adding one project. Infer lab from parent directory name. Skip to Phase 2 scanning just that directory.

---

## Step 2: Filesystem Scan

Given a lab path, scan for project boundaries.

### 2a. Discover project directories

List immediate subdirectories. For each, check for project indicators:

```bash
# List candidate directories (depth 1)
ls -d {lab_path}/*/ 2>/dev/null
```

A directory is a **project candidate** if it contains ANY of:
- `CLAUDE.md` (strong signal)
- `.git/` (strong signal)
- `data/` directory
- `analysis/` or `results/` directory
- `*.R`, `*.py`, `*.sh` files (check with ls, not deep find)
- `Snakefile`, `Nextflow`, `Makefile`
- `*.lsf`, `*.slurm`, `*.pbs` files (HPC job scripts)

Skip directories that are clearly not projects: `.git`, `__pycache__`, `node_modules`, `.Rproj.user`, `renv`, `.snakemake`.

### 2b. Extract project metadata

For each candidate project, collect:

| Field | Detection Method |
|-------|-----------------|
| name | Directory basename |
| project_tag | Lowercase, hyphens for spaces/underscores |
| languages | File extensions: .R -> R, .py -> Python, .sh -> Bash, .nf -> Nextflow |
| has_claude_md | Test `{path}/CLAUDE.md` exists |
| has_git | Test `{path}/.git/` exists |
| has_tests | Test `{path}/tests/` or `{path}/analysis/tests/` exists |
| data_files | `ls {path}/data/ 2>/dev/null \| head -10` (sample, not exhaustive) |
| hpc_indicators | Presence of .lsf/.slurm/.pbs files, or HPC paths in CLAUDE.md |

### 2c. Read CLAUDE.md for auto-population

If `CLAUDE.md` exists in a project, read it (first 100 lines) and extract:
- **Description**: first paragraph or "## Overview" section
- **Language**: from documented tech stack or dependencies
- **HPC path**: any Minerva/HPC/cluster paths mentioned
- **Scheduler**: LSF, SLURM, PBS if mentioned
- **Key data files**: from "## Data" or similar section

Do NOT read CLAUDE.md files that are excessively large (>500 lines). Read first 100 lines only.

### 2d. Output scan results

Build a structured scan report: one entry per discovered project with all auto-detected fields. Display to user as a summary table:

```
Scan results for ~/projects/Lab_Name/:

| # | Directory | Tag | Languages | Git | CLAUDE.md | Tests | Data Files |
|---|-----------|-----|-----------|-----|-----------|-------|------------|
| 1 | ProjectA  | project-a | R, Python | Y | Y | Y | 3 files |
| 2 | ProjectB  | project-b | R | Y | N | N | 12 files |
```

---

## Step 3: Diff Against Vault

Compare discovered projects against REGISTERED_TAGS from Step 0.

Classify each discovered project:

| Status | Condition | Action |
|--------|-----------|--------|
| **NEW** | project_tag not in REGISTERED_TAGS | Full onboard |
| **CHANGED** | project_tag exists but path or key metadata differs | Update |
| **CURRENT** | project_tag exists and matches | Skip |

Present diff table to user:

```
Vault diff:

| Project | Status | Detail |
|---------|--------|--------|
| project-a | NEW | Not registered in vault |
| project-b | CURRENT | Already at projects/lab/project-b.md |
| project-c | CHANGED | Path changed: old -> new |
```

If ALL projects are CURRENT and mode is not `--update`:
```
All projects already registered. Nothing to do.
Hint: Use /onboard --update to re-scan for changes.
```

**Gate: ask user to confirm which NEW/CHANGED projects to proceed with.** User may deselect specific projects.

---

## Step 4: Structured Interview

Ask targeted questions for what scanning cannot detect. Use AskUserQuestion tool.

### 4a. Lab-level questions (skip if lab already registered in _index.md)

Ask these together in one question block:
- PI name (may be auto-detected from existing projects in same lab)
- Institution and department
- Lab research focus (1-2 sentences)
- HPC details: cluster name, scheduler (LSF/SLURM/PBS), account/allocation name, base path on cluster
- If no HPC: confirm with "Does this lab use HPC? (No is fine)"

### 4b. Per-project questions (only for NEW/CHANGED projects)

For each new project, ask:
- **Research domain** (offer detected options + Other): e.g., "AD/neurodegeneration", "Cancer biology", "Metagenomics", "Immune aging"
- **Key research question** (1-2 sentences): what is this project trying to answer?
- **Data source description**: where does the data come from? (lab-generated, public repository, clinical cohort, etc.)
- **Linked research goals**: show existing goals from `_research/goals/` as selectable options + "New goal" + "None"
- **Omic layer classification**: which omic layers? (Genomics, Transcriptomics, Proteomics, Metabolomics, Epigenomics, Metagenomics, Clinical/EHR -- multi-select)

Auto-fill what you can from CLAUDE.md scan. Only ask about fields that could not be detected.

### 4c. Strategic questions (on full onboard only, skip on --update and single-add)

Ask once at the end:
- Are there active research directions not captured by existing projects?
- Any upcoming datasets or collaborations?
- Any cross-project synergies you want to highlight?
- Any pending data access applications? (cohort name, status)

---

## Step 5: Generate Artifacts

**CRITICAL: Present a summary of ALL artifacts to be created BEFORE writing anything. Get explicit user approval.**

Show:
```
Artifacts to create:

Project Notes:
  - projects/{lab}/{tag}.md  (for each NEW project)

Symlinks:
  - _dev/{tag} -> {project_path}  (for each NEW project)

Index Updates:
  - projects/_index.md  (add rows to {lab} section)

Data Inventory:
  - _research/data-inventory.md  (add entries for projects with identifiable data)

Research Goals (if any new directions identified):
  - _research/goals/{goal-slug}.md

Goals Update:
  - self/goals.md  (append new threads)

Reminders:
  - ops/reminders.md  (follow-up items)

Proceed? (Y/n)
```

### 5a. Project Notes

For each NEW project, build a project note. Follow the exact schema from `_code/templates/project.md`:

```yaml
---
type: project
title: "{detected or user-provided title}"
project_tag: "{tag}"
lab: "{lab name}"
pi: "{PI}"
status: active
project_path: "{absolute or ~-relative path}"
language: [{detected languages}]
hpc_path: "{from interview, or empty string if none}"
scheduler: "{LSF, SLURM, or PBS if detected; otherwise empty string}"
linked_goals: [{from interview, as wiki-links}]
linked_hypotheses: []
linked_experiments: []
has_claude_md: {true/false}
has_git: {true/false}
has_tests: {true/false}
created: {today YYYY-MM-DD}
updated: {today YYYY-MM-DD}
tags: [project, {lab-slug}-lab]
---

{One-line description from CLAUDE.md or interview}

![[_dev/{tag}/CLAUDE.md]]
```

### 5a2. Internal Doc Discovery

After generating the base project note, scan the project directory for internal documentation that should be wiki-linked from the project note. Without these links, symlinked `.md` files appear as graph orphans in Obsidian.

**Discovery:**
```bash
find {project_path} -maxdepth 5 -name '*.md' \
  -not -path '*/.git/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/.pytest_cache/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/.snakemake/*' \
  -not -path '*/renv/*' \
  -not -path '*/.claude/plans/*' \
  -not -path '*/.serena/*' \
  -not -path '*/.github/*' \
  -not -path '*/dist-info/*' \
  2>/dev/null | sort
```

**Filter noise:**
- Exclude files < 100 bytes
- Exclude CLAUDE.md (already transcluded above)
- Exclude generic cache/build directory READMEs
- Exclude `.claude/plans/` agent plan artifacts

**Present to user:**
Show discovered docs as a checklist with file sizes:
```
Internal docs found in {project_path}:

[x] README.md (4.7K) -- project overview
[x] analysis/docs/ARCHITECTURE.md (17K) -- system architecture
[x] analysis/docs/investigations/README_FACTORIAL.md (7.4K) -- factorial experiment design
[ ] .github/PULL_REQUEST_TEMPLATE.md (1.2K) -- PR template

Which should be linked from the project note?
```

Use AskUserQuestion with multiSelect to let the user choose.

**Generate Key Docs section:**
For each selected doc, append a `## Key Docs` section to the project note body (after the `![[_dev/{tag}/CLAUDE.md]]` line):

```markdown
## Key Docs
- [[ARCHITECTURE]] -- system architecture and module boundaries
- [[README_FACTORIAL]] -- 2x2x2 factorial experiment design
```

Context phrases are **required** for every entry (same convention as topic map Core Ideas). A bare link list is insufficient.

**Skip conditions:**
- If no `.md` files found besides CLAUDE.md, skip this step silently.
- If user deselects all docs, skip without adding the section.

Present each project note to user for approval/edits before saving.

Save to: `projects/{lab_slug}/{tag}.md` (matching existing convention: `projects/elahi/`, `projects/chipuk/`, `projects/kuang/`).

Create lab subdirectory if it does not exist:
```bash
mkdir -p projects/{lab_slug}
```

### 5b. Symlinks

For each NEW project:
```bash
ln -sfn {project_path} {vault_root}/_dev/{tag}
```

Verify _dev/ directory exists first:
```bash
mkdir -p _dev
```

If symlink already exists and points to the same target, skip silently (idempotent).

After creating individual symlinks, run the bulk verification script to catch any missed links:
```bash
bash ops/scripts/create-dev-links.sh
```
This script reads all project notes and ensures every `project_tag` has a corresponding `_dev/` symlink. It is idempotent.

### 5b2. Lab Entity Node

If `projects/{lab_slug}/_index.md` does not exist, create it using the `_code/templates/lab.md` schema:

```yaml
---
type: lab
lab_slug: "{lab_slug}"
pi: "{PI name}"
institution: "{from interview}"
hpc_cluster: "{from interview or empty}"
hpc_scheduler: "{from interview or empty}"
research_focus: "{1-2 sentence focus}"
created: {today}
updated: {today}
tags: [lab]
---
```

The body should list the lab's projects and datasets. Filename becomes the `[[lab_slug-lab]]` link target (e.g., `projects/elahi/_index.md` renders as `[[elahi-lab]]` in Obsidian if configured, or link directly to the `_index` file).

### 5c. Update projects/_index.md

For each NEW project, append a row to the appropriate lab section table in `projects/_index.md`.

Row format (matching existing convention):
```
| [[{tag}]] | {PI} | {languages, comma-separated} | {HPC info or --} | {one-line summary} |
```

If the lab section does not exist, create it:
```markdown
### {Lab Name}

| Project | PI | Language | HPC | Summary |
|---|---|---|---|---|
| [[{tag}]] | {PI} | {languages} | {HPC or --} | {summary} |
```

Insert new lab sections before the `## Maintenance` line.

### 5d. Data Inventory

For each NEW project that has identifiable datasets (data/ directory is non-empty, or data described in CLAUDE.md or interview):

**Summary Table row** -- append to the Summary Table in `_research/data-inventory.md`:
```
| **{Dataset Name}** | {Lab} | {Domain} | {Omic layers} | {N or TBD} | {Species} | {Access status} | {Location/project} |
```

**Omic Coverage Matrix row** -- append to the Omic Coverage Matrix:
```
| {Dataset Name} | {Genomics or --} | {Transcriptomics or --} | ... | {Clinical/EHR or --} |
```

**Detailed Inventory entry** -- append under the appropriate lab heading in the Detailed Inventory section:
```markdown
#### {Dataset Name}

- **Project:** [[{tag}]]
- **Path:** `{project_path}`
- **Source:** {from interview or CLAUDE.md}
- **N:** {sample count or TBD}
- **Data types:** {omic layers and specifics}
- **Status:** {current status}
```

Use the exact column format of existing entries. Do not reformat existing content.

### 5e. Research Goals

If the strategic interview identified new research directions not covered by existing goals:

1. Check `_research/goals/` for existing goals that might match.
2. If genuinely new, create a research goal note using `_code/templates/research-goal.md` schema:

```yaml
---
type: research-goal
title: "{goal title}"
status: active
constraints: []
evaluation_criteria: []
domain: "{domain}"
tags: [research-goal]
created: {today}
---
```

3. Present to user for approval before saving.
4. Save to `_research/goals/{goal-slug}.md`.

If a goal already exists that matches what the user described, link the new projects to it instead of creating a duplicate.

### 5f. Cross-Lab Bridge Claims

If cross-project synergies were identified in Step 4c, generate bridge claims in `notes/`. These capture shared methodology, platform overlap, or mechanistic connections between labs.

Each bridge claim MUST follow the `_code/templates/claim-note.md` schema exactly, including:

```yaml
---
description: "{adds context beyond title -- shared target, transferable method, or mechanistic link}"
type: pattern
confidence: preliminary
created: {today YYYY-MM-DD}
---
```

Body: explain the connection with inline wiki-links to relevant project tags and hypotheses.

**CRITICAL: Every bridge claim MUST end with a Topics: section** linking to the relevant topic map(s):

```markdown
Topics:
- [[relevant-topic-map]]
```

Present each bridge claim to user for approval before saving. Skip if user confirms no genuine synergies exist (do not force connections).

### 5g. Update self/goals.md

Append new entries to the `## Active Threads` section:
```
- {Lab Name} onboarded -- {N} projects registered, linked to {goals or "no goals yet"}
```

If new research goals were created, add them under `## Active Research Goals` following the existing format:
```
### [[{goal-slug}]] -- {goal title}
**Scope:** {from interview}
**Status:** Newly created. Next: /literature search + /generate hypotheses.
```

### 5h. Update ops/reminders.md

Add follow-up items for incomplete work:
```
- [ ] {today}: Complete data inventory for {project} -- detailed entry needed
- [ ] {today}: Run /reflect to connect new {lab} projects to existing claims
- [ ] {today}: Apply for {cohort} access -- needed for {goal}
- [ ] {today}: Run /reduce on {project}/CLAUDE.md for knowledge extraction
```

Only add reminders for genuinely actionable follow-ups. Do not add reminders for projects that are fully onboarded with no gaps.

---

## Step 6: Verify

Run validation on all created artifacts:

### 6a. Schema check
For each created project note, verify required YAML fields are present:
- type, title, project_tag, lab, pi, status, project_path, language, hpc_path, scheduler, linked_goals, linked_hypotheses, linked_experiments, has_claude_md, has_git, has_tests, created, updated, tags

### 6b. Link health
Check that all `[[wiki-links]]` in created/modified files resolve to real files:
```bash
# Extract wiki-links from new files and check each resolves
```

### 6c. Index sync
Verify every new project note has a corresponding row in `projects/_index.md`.

### 6d. Symlink check
Verify each `_dev/{tag}` symlink exists and points to a valid directory:
```bash
ls -la _dev/{tag}
```

### 6e. Data inventory consistency
Every project with a non-empty data/ directory should have at least a Summary Table entry in `_research/data-inventory.md`.

Report any issues found. If all pass:
```
Verification: all checks passed.
```

---

## Step 7: Summary Report

Output a summary of everything done:

```
=== /onboard Summary ===

Lab: {lab name} ({lab path})
Mode: {full | incremental | single-add}

Projects registered: {N}
{list with tags and one-line summaries}

Data inventory entries added: {N}
Research goals created: {N} ({list or "none"})
Symlinks created: {N}

Follow-up reminders added:
{list}

Suggested next actions:
- /reflect -- connect new projects to existing knowledge graph
- /reduce on CLAUDE.md files -- extract detailed knowledge
- /research -- define hypotheses for new research goals
- /literature -- search for relevant papers in new domains
=== End Summary ===
```

---

## Handoff Mode

If `--handoff` was included in arguments, append RALPH HANDOFF block after the summary:

```
=== RALPH HANDOFF: onboard ===
Target: {lab path}

Work Done:
- Scanned {lab path}: found N projects (M new, K current)
- Created project notes: {list}
- Updated data-inventory.md: {N entries added}
- Created research goals: {list or "none"}
- Updated self/goals.md, projects/_index.md

Files Modified:
- {list of all files created/modified with action: CREATE or EDIT}

Learnings:
- [Friction]: {any friction encountered} | NONE
- [Surprise]: {any surprises} | NONE
- [Methodology]: {any methodology insights} | NONE

Queue Updates:
- Suggest: /reflect to connect new projects to existing claims
- Suggest: /reduce on CLAUDE.md files for detailed knowledge extraction
=== END HANDOFF ===
```

---

## Error Handling

| Error | Behavior |
|-------|----------|
| Lab path does not exist | Report error with path checked, ask for correct path |
| No projects detected in path | Report what was scanned and indicators checked, ask if path is correct |
| CLAUDE.md parse failure | Log warning, fall back to filesystem detection only |
| Project already registered | Show as CURRENT in diff, skip unless mode is --update with changes |
| data-inventory.md missing | Create with header template from `_code/templates/` |
| _dev/ directory missing | Create with `mkdir -p _dev` |
| _dev/ symlink already exists pointing to same target | Skip silently (idempotent) |
| _dev/ symlink exists pointing to different target | Warn user, ask before overwriting |
| Research goal already exists | Link project to existing goal instead of creating duplicate |
| projects/{lab}/ directory missing | Create with `mkdir -p` |
| Permission denied on symlink | Report error, suggest manual creation, continue with remaining artifacts |

---

## Critical Constraints

- **User approval before every write.** Never silently create artifacts.
- **Match existing conventions exactly.** Project notes go in `projects/{lab_slug}/`. Index uses the existing table format. Data inventory uses existing column format.
- **Idempotent.** Running /onboard twice on the same lab produces no duplicate artifacts.
- **No CLAUDE.md content duplication.** Project notes use `![[_dev/{tag}/CLAUDE.md]]` transclusion, not copied content.
- **Wiki-link integrity.** Every link created must resolve. Verify before finishing.
- **YAML safety.** Double-quote all string values in frontmatter.
- **No slash in tags or titles.** Use hyphens: `elahi-lab` not `elahi/lab`.

---

## Why This Skill Exists

Onboarding a lab manually requires running /project per project, hand-editing data-inventory.md, creating research goals individually, and manually wiring everything together. This skill automates the full flow through hybrid detection (filesystem scanning + structured interview), producing all vault artifacts in one pass. It also supports incremental re-runs when new projects or datasets arrive.

## Skill Graph

Invoked by: user (standalone), /ralph (delegation)
Invokes: (none -- leaf agent, but suggests /reflect, /reduce, /research as follow-ups)
Reads: projects/, _research/data-inventory.md, _research/goals/, self/goals.md, ops/reminders.md, filesystem
Writes: projects/, _research/data-inventory.md, _research/goals/, self/goals.md, ops/reminders.md, projects/_index.md, _dev/ symlinks
