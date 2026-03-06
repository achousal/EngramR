# Static Plot Conventions

Conventions for PDF/SVG publication-quality figures produced with ggplot2 (R) or matplotlib/seaborn (Python). Lab-specific color choices live in `styles/labs/`. Project-specific overrides live in `styles/projects/`.

## General Rules

- Output format: PDF (vector) by default. PNG only when raster is required (e.g. heatmaps with many cells).
- Aspect ratios: prefer 16:9-friendly dimensions for presentations. Square for single-panel figures.
- Theme: `theme_minimal()` base with lab-specific overrides.
- Font: system sans-serif at print scale (base_size 11-12).

## Scatter Plots

| Detail | Value |
|--------|-------|
| Trend lines | `geom_smooth(method = "lm")`, linewidth 0.8, ribbon alpha 0.2 |
| Overplotting | Use `geom_smooth` only (no raw points) when n > 200 |
| Annotation labels | `geom_label`, top-right corner (`x=Inf, y=Inf, hjust=1, vjust=1`) |
| Annotation content | r, p-value, n per group; p-value format: `p<0.001` threshold, else 3 decimal places |
| Correlation | 2 decimal places |

## Box/Violin Plots

| Detail | Value |
|--------|-------|
| Y-axis floor | Zero (`limits = c(0, NA)`) |
| Jitter points | size 1.5, alpha 0.6, jitter.width 0.1-0.2 |
| Violin y-axis expand | `c(0.05, 0.25)` -- 5% bottom for n-labels, 25% top for brackets |
| Box y-axis expand | `c(0, 0.10)` -- no bottom padding, 10% top for brackets |

## Heatmaps

| Detail | Value |
|--------|-------|
| Diverging fill | Blue-white-red, midpoint=0, limits [-1,1] |
| Sequential fill | `Blues` |
| Cell text | r value + n per cell |
| Grid | `panel.grid = element_blank()` |
| X-axis | 45-degree rotation |

## Faceting

- Use `facet_grid2()` (ggh4x) with `independent = "y"` when biomarkers have different scales.
- Use `facet_wrap()` for single-variable facets with free scales.
- Grey strip bars for labels (default ggplot2).

## Annotation Style

| Detail | Value |
|--------|-------|
| Font size | 2.0 (geom_label) |
| Box style | white fill, grey30 text, 0.3pt border |
| P-value format | `p<0.001` threshold, else 3 decimal places |

## Table 1 (Cohort Summary)

Every project with a defined cohort produces a Table 1.

### Structure

| Section | Variables | Format |
|---------|-----------|--------|
| Demographics | Age, Sex, Race/Ethnicity, BMI | continuous: `mean (SD)`; categorical: `n (%)` |
| Clinical | markers, eGFR, creatinine, etc. | continuous: `mean (SD)` |
| Comorbidities | diabetes, hypertension, etc. | binary: `n (%)` |

### Column layout

- One column per group: `"Group A (n = X)"`, `"Group B (n = Y)"`.
- n embedded directly in the column header.
- Optional SMD column for balance assessment.
- Section headers as row separators (bold or shaded).

### Output formats

- **CSV** (machine-readable, version-controlled): `results/tables/table1.csv`
- **Rendered figure** (manuscript-ready): `results/tables/table1.png` + `.svg`

### Implementation

R: `gtsummary::tbl_summary()` or `tableone::CreateTableOne()`. Python: `make_table1(df, output_path)` in `analysis/table1.py`.
