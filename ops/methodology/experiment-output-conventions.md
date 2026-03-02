---
description: "Standard conventions for experiment output directory structure, file naming, execution logging, and cross-repo synchronization"
type: methodology
created: 2026-02-25
source: "EXP-002 retrospective"
---

# Experiment Output Conventions

Established after EXP-002 LPS cycle retrospective. Applies to all future experiments.

## Results Directory Structure

Every experiment results directory must contain:

```
results/{exp-id}/
  README.md              <- file manifest, naming key, reproducibility info (required)
  execution_log.yaml     <- structured step timeline with status (required)
  data/                  <- processed data artifacts
  figures/               <- plots, named by step
  gates/                 <- pre-analysis gate decision records
  rdata/                 <- R serialized objects
  reports/               <- text reports, final synthesis
  tables/                <- summary tables, named by step
```

## File Naming Convention

Step-based naming: `{step}_{description}.{ext}`

- `step{NN}_` prefix matches the pipeline script number (01, 02, 03...)
- `step{NN}{letter}_` for sub-steps (04b_sensitivity)
- `gate{N}_` prefix for pre-analysis gate artifacts
- No paper-style numbering (fig01, table4, figS1) -- name by what the file IS

Rationale: paper-style numbering assumes a publication that may never exist. Step-based naming maps directly to the analysis pipeline, making it immediately clear which script produced which output.

## README.md (Required)

Must contain:
- Experiment ID and brief outcome
- Directory structure diagram
- File manifest tables: filename -> source script -> SAP prediction -> description
- Which files were generated vs. skipped (and why)
- Naming convention reference
- Reproducibility info: seeds, checksums, package versions

Template: `_code/templates/experiment-results-readme.md`

## execution_log.yaml (Required)

Structured log:
```yaml
steps:
  - id: step01_preprocessing
    script: 01_preprocessing.R
    started: "ISO timestamp"
    completed: "ISO timestamp"
    status: done
    seed: 42
    note: "brief summary"
    outputs: [list of files]

skipped:
  - id: step05_deconv_wgcna
    reason: "Gate 4 STOP"
```

## Data Provenance

- `run_metadata.txt` must include SHA256 checksum of raw data files
- Use `compute_data_checksum()` from config (requires `digest` package)

## Cross-Repo Sync Checklist

When experiment completes in a lab directory, update the EngramR vault:
1. Hypothesis frontmatter: status, outcome fields
2. Execution tracker: step status column
3. Research goal: empirical findings section
4. Copy key results summary into experiment note body

## Lessons from EXP-002

- Gate system worked well -- Gate 4 STOP saved time on phases 5-13
- The gate4_synthesis.txt as a single "tell the whole story" document was the most useful output
- Paper-style figure numbering created gaps and confusion (fig03 missing because Gate 4 STOP)
- Results directory without README made it hard to understand what each file was
- Two-repo split (knowledge vs execution) requires explicit sync discipline
