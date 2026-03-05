---
description: "Pointer to the biomarker dashboard project, now a standalone repository"
type: development
status: extracted
created: 2026-03-02
updated: 2026-03-05
---

# Patient Biomarker Dashboard -- Extracted

The biomarker dashboard has been extracted to a standalone project:

**Location**: `~/Projects/Elahi_Lab/biomarker-dashboard/`

## What stays in EngramR

- `_code/profiles/bioinformatics/panels/*.json` -- lab-specific panel configs
- `_code/profiles/bioinformatics/dashboard_config.yaml` -- lab branding
- `_code/R/export_predictions.R` -- R template for prediction JSON export

## Why extracted

- Independent build lifecycle (Vite + TypeScript) separate from vault tooling
- Different consumers (clinicians vs researchers)
- Shareable with other labs without cloning the vault
- Cleaner CI -- no JS dependency tree in a Python/R repo
