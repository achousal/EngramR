# Cross-Project Plot Style Guide

Authoritative visual style reference for all research plots across Elahi, Chipuk, and Kuang labs. Supersedes per-project theme definitions. AD-pipeline-specific details remain in `PLOT_DESIGN.md` (this directory). Lab-specific color palettes live alongside in `elahi.md`, `chipuk.md`, etc.

## Philosophy

Let the data dominate. Structural elements -- axes, frames, labels -- should recede into the background so the reader's eye goes to the data first. We use a clean, minimal aesthetic inspired by publication-quality figures: no gridlines, no background fills, no decorative elements. Every visual decision serves either clarity (can the reader parse the data?) or honesty (does the presentation faithfully represent the underlying distribution?).

Every figure should be self-contained: a reader seeing only the plot (no surrounding text) should know the sample size, which test was used, and where to find exact p-values. Pair every analysis script with a stats report, a Table 1 for cohort context, and an NA summary when missingness is non-trivial. These deliverables are not optional extras -- they are part of a complete analysis.

## Frame and structure

Foundation: `theme_classic` (R) / `classic` style (Python), which gives a white background with axis lines only.

- **Spines**: left and bottom only (top and right removed), linewidth ~0.8.
- **Gridlines**: none. Grid adds visual noise that competes with data; axis ticks are sufficient for value reading.
- **Background fill**: white, no panel shading.

This combination produces a clean "L-shaped" frame that anchors the data without boxing it in. Apply via `theme_research()` (R) or `apply_research_theme()` (Python).

## Typography

- **Base font size**: 14pt, sans-serif.
- **Titles**: bold. Creates hierarchy without decoration.
- **Facet strip backgrounds**: grey90 (`#E5E5E5`), no border, bold text. Subtle enough to label panels without heavy frames.
- **Legend position**: bottom by default. Maximizes the plot area and reads as a natural caption beneath the figure.

## Distribution plots (violin and box)

Distribution plots use semi-transparent fills with individual data points overlaid. This dual-layer approach shows both the distribution shape and the raw observations.

- **Fill alpha**: 0.35--0.40. Transparent enough to see overlaid points; opaque enough to convey the distribution shape.
- **Individual points**: jittered, alpha 0.5--0.6, size 1.5--5 depending on n. Points give the reader a sense of sample size and outlier structure that summary geometry alone cannot convey.
- **Structural elements**: black whiskers, caps, and medians at linewidth ~1.0. Black structural lines anchor the summary statistics against the colored fills.
- **Outliers**: hidden when jitter points are present (they would duplicate information).
- **Dodge width**: 0.7 for grouped comparisons (e.g., Male/Female side by side).

### Violin specifics

- Untrimmed (shows full kernel density extent).
- Violin outline linewidth 0.4 (subtle).
- Mean marker: shape 95 (dash), size 6, black.

### Box specifics

- Box width 0.35 (narrow for clean dodged layout).
- Box outline linewidth 0.6.

## Scatter plots

- **Point alpha**: 0.6. Balances visibility of individual points against overplotting.
- **White edges**: 0.5pt white stroke around each point. Separates overlapping points and improves readability against colored backgrounds or dense clusters.
- **Regression lines**: linewidth 0.8 with confidence interval fill at alpha 0.18--0.2. The CI ribbon should be visible but not dominate the data layer.

## Statistical annotation box

A consistent annotation box for embedding test results directly in the figure.

- **Background**: wheat fill, alpha 0.8. A warm neutral tone that stands out from white backgrounds without competing with data colors.
- **Shape**: rounded corners, padding 0.3.
- **Position**: top-left (or top-right for scatter panels). Consistent placement creates a visual anchor so the reader always knows where to find statistics.
- **Content**: p-values, effect sizes, sample sizes -- whatever the analysis requires.
- **Font size**: small (2.0--2.5) relative to base. Readable at export resolution but does not dominate.

## Reference lines

- **Color**: gray.
- **Style**: dashed or dotted, linewidth 1.0.
- **Purpose**: threshold markers (e.g., significance cutoffs on volcano plots, baseline values). Gray dashed lines indicate reference values without demanding attention.

## Heatmaps

- **Diverging data** (centered at 0): `RdBu` (R) / `RdBu_r` (Python). Perceptually uniform, colorblind-safe, widely recognized as the standard for diverging scales.
- **Sequential data** (density, counts): `Blues`. Clean single-hue ramp that avoids implying a midpoint.
- **Cell borders**: none. Clean tile appearance.

## Output standards

- **Default format**: PDF (vector, publication-ready).
- **Configurable**: `fmt` parameter accepts `"pdf"`, `"png"`, `"svg"`, `"tiff"`.
- **DPI**: 300 for all raster output.
- **Tight layout**: `bbox_inches="tight"` (Python), no wasted whitespace.
- **Sidecar**: optional `_pvalues.txt` alongside every figure with exact p-values (`save_pvalues()` / `save_figure(sidecar_text=...)`).

## Standard figure sizes (inches)

| Plot type | Key | Width x Height |
|-----------|-----|----------------|
| Box/violin (grouped) | `box_grouped` / `violin_grouped` | 8 x 6 |
| Box/violin (single) | `box_single` / `violin_single` | 6 x 6 |
| Scatter (multi-panel) | `scatter_multi` | 18 x 7 |
| Scatter (single pop) | `scatter_single` | 14 x 8 |
| Scatter (bivariate) | `scatter_bivar` | 10 x 6 |
| Correlation heatmap | `heatmap` | 10 x 6 |
| Forest plot | `forest` | 10 x 8 |
| Volcano plot | `volcano` | 10 x 8 |
| ROC curve | `roc` | 7 x 7 |
| Bar + error bars | `bar` | 8 x 6 |

Access via `get_figure_size("roc")` or `FIGURE_SIZES["roc"]`.

## Statistical decision tree

```
two_group (unpaired):
  n >= 30 AND normal -> Welch t-test
  n < 30 OR non-normal -> Mann-Whitney U

multi_group (3+):
  Kruskal-Wallis + Dunn post-hoc (BH correction)

paired (2-group):
  normal -> paired t-test
  non-normal -> Wilcoxon signed-rank

correlation:
  default -> Spearman
  if explicitly requested + normal -> Pearson

proportion:
  any expected cell < 5 -> Fisher exact
  all expected cells >= 5 -> Chi-square
```

Use `select_test()` (R or Python) to get the recommended test name. Use `run_test()` / `run_two_group()` / `run_correlation()` to execute.

## Annotation standards

- **P-value display**: `p < 0.001` for very small; else 3 decimal places (`format_pval()`)
- **Stars**: `***` (p<0.001), `**` (p<0.01), `*` (p<0.05), `ns` (`pval_stars()`)
- **Correlation annotation**: `r = X.XX, p = Y.YYY, n = Z` (`format_correlation()`)
- **Sidecar file**: exact p-values saved as `_pvalues.txt` alongside every figure (`save_pvalues()`)

## Sample size display (n)

Sample sizes must be visible in every figure. The reader should never have to guess how much data backs a result.

### In distribution plots (violin, box, bar)

- **Position**: at `y = 0` (or `y = -Inf` if zero is not meaningful), below each group.
- **Style**: italic, size 3, `vjust = 1.5`.
- **Format**: `n=N` (lowercase n, no spaces around `=`).
- **For dodged groups**: position each label at the dodged x-offset (e.g., Male at `x - 0.175`, Female at `x + 0.175`).

```r
# R pattern (reference implementation)
n_labels <- df %>%
  group_by(group, subgroup) %>%
  summarise(N = n(), .groups = "drop") %>%
  mutate(label = paste0("n=", N))

geom_text(data = n_labels, aes(x = x, y = 0, label = label),
          inherit.aes = FALSE, size = 3, fontface = "italic", vjust = 1.5)
```

### In scatter / correlation plots

- **Inline in annotation**: include `n=N` as part of the stats text (e.g., `r = 0.51, p < 0.001, n = 68`).
- **In legend entries**: append n to group label when groups differ in size (e.g., `CKD (n=45)`).
- **In x-axis tick labels**: use `"Group\n(n = N)"` format when group n is the primary context.

### In forest plots

- **Row-level**: annotate `n=N, p=X.XXX` to the right of each confidence interval.

### Convention

Use lowercase `n=` consistently. Reserve uppercase `N=` only for total sample size in report headers. Always use `n=` (no space) in compact plot annotations; `n = ` (with spaces) is acceptable in longer prose-style stat boxes.

## Statistical annotation in figures

Every figure with a statistical comparison must name the test used. The reader should not need to consult a methods section to interpret the annotation.

### In the stat box (wheat background)

Include the test name as the first element:

```
Mann-Whitney p = 0.003
GM ratio (CKD/Ctrl) = 1.42
```

```
Spearman rho = 0.51
95% CI [0.33, 0.65]
p < 0.001
n = 68
```

### In significance brackets (ggpubr)

Brackets show stars (`{p.signif}`) for quick scanning. The test name goes in the stat box or figure caption, not on the bracket itself.

### In legends

When comparing groups with different tests across panels, add the test name to the legend or subtitle:

```r
labs(subtitle = "Mann-Whitney U test; bars show median + IQR")
```

## Stats report

Every analysis script produces a companion plain-text stats report. This is the canonical pattern.

### Structure

```
{Analysis Name} - Statistical Report
Generated: {timestamp}

--- Settings ---
{settings tibble or dict: IQR k, flags, thresholds}

--- Sample Counts ---
{rows before/after filters, per group}

--- Outlier Summary ---
{per-variable: N_total, N_outliers, pct_outliers, bounds}

--- Results ---
{per-comparison block:}
  Group / Subgroup:
    N = {n}
    r = {value} {stars}
    p = {value}
  Fisher Z: z={value}, p={value}
  Interaction: p={value}
```

### Implementation

```r
# R pattern (sink)
sink(file.path(results_dir, "stats_report.txt"))
cat("Analysis - Statistical Report\n")
cat("Generated:", format(Sys.time()), "\n\n")
# ... print results ...
sink()
```

```python
# Python pattern (pathlib)
report_path = results_dir / "stats_report.txt"
lines = [
    f"Analysis - Statistical Report",
    f"Generated: {datetime.now().isoformat()}",
    "",
    "--- Settings ---",
    # ...
]
report_path.write_text("\n".join(lines), encoding="utf-8")
```

### Non-negotiables

- Always include a timestamp.
- Always include sample sizes per group.
- Always include the test name for every comparison.
- Stars and formatted p-values for quick scanning; exact p-values for rigor.
- Save alongside the figures in the same `results/` subdirectory.

## Table 1 (cohort summary)

Every project with a defined cohort produces a Table 1. This is the standard demographic/clinical summary that grounds the analysis.

### Structure

| Section | Variables | Format |
|---------|-----------|--------|
| Demographics | Age, Sex, Race/Ethnicity, BMI | continuous: `mean (SD)`; categorical: `n (%)` |
| Clinical | biomarkers, eGFR, creatinine, etc. | continuous: `mean (SD)` |
| Comorbidities | diabetes, hypertension, etc. | binary: `n (%)` |

### Column layout

- One column per group: `"Group A (n = X)"`, `"Group B (n = Y)"`.
- n embedded directly in the column header.
- Optional SMD column (standardized mean difference) for balance assessment.
- Section headers as row separators (bold or shaded).

### Output formats

- **CSV** (machine-readable, version-controlled): `results/tables/table1.csv`
- **Rendered figure** (manuscript-ready): `results/tables/table1.png` + `.svg`

### Implementation reference

The reference implementation is `make_table1(df, output_path)` (Python, `analysis/table1.py`). For R projects, use `gtsummary::tbl_summary()` or `tableone::CreateTableOne()` to produce equivalent output.

## NA summary report

When missingness is non-trivial (any variable with >0% NA after filtering), produce an NA summary alongside the stats report.

### Structure

| Column | Description |
|--------|-------------|
| `variable` | Column name |
| `group` | Cohort group (e.g., CKD, Control) |
| `n_missing` | Count of NAs |
| `pct_missing` | Percentage missing |
| `record_ids` | Semicolon-separated IDs of affected records |

### Output

- **CSV**: `results/tables/na_summary.csv`
- Report only (variable, group) pairs with at least one NA -- do not pad with zero rows.

### Implementation reference

The reference implementation is `na_summary()` in `analysis/load_clean.py`. For R projects:

```r
na_summary <- df %>%
  tidyr::pivot_longer(cols = analysis_vars, names_to = "variable") %>%
  dplyr::filter(is.na(value)) %>%
  dplyr::group_by(variable, group) %>%
  dplyr::summarise(
    n_missing = dplyr::n(),
    pct_missing = round(100 * dplyr::n() / nrow(df), 1),
    record_ids = paste(id, collapse = "; "),
    .groups = "drop"
  )
readr::write_csv(na_summary, file.path(results_dir, "tables", "na_summary.csv"))
```

### When to produce

- Always check. If all variables are complete after filtering, log that fact in the stats report ("No missing values in analysis variables") rather than producing an empty CSV.
- If missingness exceeds 10% for any variable, flag it prominently in the stats report header.

## Analysis deliverables checklist

Every analysis script should produce the following outputs in `results/`:

| Deliverable | File pattern | Required? |
|-------------|-------------|-----------|
| Figures (PDF primary) | `results/figures/*.pdf` | Yes |
| P-value sidecar | `results/figures/*_pvalues.txt` | Yes (use `save_pvalues()`) |
| Stats report | `results/stats_report.txt` | Yes |
| Table 1 | `results/tables/table1.csv` + `.png` | Yes (if cohort-based) |
| NA summary | `results/tables/na_summary.csv` | Yes (if any missingness) |
| Model tables | `results/tables/table2_*.csv` | When regression/models used |

## Colors

Lab-specific categorical palettes and color policies are documented alongside this file:

| Lab    | Style sheet                          | Palette                     |
| ------ | ------------------------------------ | --------------------------- |
| Elahi  | [`elahi.md`](./elahi.md) | ColorBrewer Set1 (8 colors) |
| Chipuk | [`chipuk.md`](./chipuk.md) | Okabe-Ito (8 colors)        |
| Kuang  | (future)                             | Set1 (defaults to Elahi)    |

Access via `lab_palette("elahi")` (R) or `get_lab_palette("elahi")` (Python). Scale helpers: `scale_color_lab("elahi")`, `scale_fill_lab("elahi")`.

### Universal semantic palettes

These mappings are lab-agnostic and apply to all projects:

| Mapping | R accessor | Python accessor | Hex |
|---------|-----------|-----------------|-----|
| Direction: Up | `DIRECTION_COLORS["Up"]` | `DIRECTION_COLORS["Up"]` | `#E41A1C` |
| Direction: Down | `DIRECTION_COLORS["Down"]` | `DIRECTION_COLORS["Down"]` | `#377EB8` |
| Direction: NS | `DIRECTION_COLORS["NS"]` | `DIRECTION_COLORS["NS"]` | `#999999` |
| Significance: sig | `SIG_COLORS["sig"]` | `SIG_COLORS["sig"]` | `#E41A1C` |
| Significance: not sig | `SIG_COLORS["not sig"]` | `SIG_COLORS["not sig"]` | `#999999` |

Scale helpers: `scale_color_direction()`, `scale_fill_direction()`, `scale_color_sig()`, `scale_fill_sig()`.

## Source files

| Language | Module | Path |
|----------|--------|------|
| R | Theme | `_code/R/theme_research.R` |
| R | Palettes | `_code/R/palettes.R` |
| R | Stats helpers | `_code/R/stats_helpers.R` |
| R | Plot builders | `_code/R/plot_builders.R` |
| R | Axis/save helpers | `_code/R/plot_helpers.R` |
| Python | Theme + palettes | `_code/src/engram_r/plot_theme.py` |
| Python | Stats helpers | `_code/src/engram_r/plot_stats.py` |
| Python | Plot builders | `_code/src/engram_r/plot_builders.py` |

## Plot builder catalog

Each builder applies `theme_research()` and accepts palette/title overrides.

| Builder | R | Python |
|---------|---|--------|
| Violin + strip | `build_violin()` | `build_violin()` |
| Box + strip | `build_box()` | `build_box()` |
| Scatter (+LM) | `build_scatter()` | `build_scatter()` |
| Heatmap | `build_heatmap()` | `build_heatmap()` |
| Volcano | `build_volcano()` | `build_volcano()` |
| Forest | `build_forest()` | `build_forest()` |
| ROC curve | `build_roc()` | `build_roc()` |
| Bar + errors | `build_bar()` | `build_bar()` |

## Usage examples

### R

```r
source("_code/R/palettes.R")
source("_code/R/theme_research.R")
source("_code/R/stats_helpers.R")
source("_code/R/plot_builders.R")
source("_code/R/plot_helpers.R")

# Select and run a test
test_name <- select_test("two_group", n_per_group = 50, normal = FALSE)
result <- run_two_group(group_a, group_b, test = test_name)

# Build and save a plot
p <- build_violin(df, group, value, fill = sex, palette = SEX_COLORS)
save_plot(p, "results/violin.pdf",
          width = FIGURE_SIZES$violin_grouped["width"],
          height = FIGURE_SIZES$violin_grouped["height"],
          pvalues = c("A vs B" = result$p.value))
```

### Python

```python
from engram_r.plot_theme import apply_research_theme, SEX_COLORS, save_figure  # Elahi palette
from engram_r.plot_stats import select_test, run_test, format_pval
from engram_r.plot_builders import build_violin

apply_research_theme()

test_name = select_test("two_group", 50, normal=False)
result = run_test(group_a, group_b, test=test_name)

fig, ax = build_violin(df, "group", "value", hue="sex", palette=SEX_COLORS)
save_figure(fig, "results/violin",
            sidecar_text=f"A vs B\t{format_pval(result.pvalue)}\n")
```

## HPC sourcing

Add `_code/R/` as a git submodule in each HPC project for versioned, reproducible access.

```bash
git submodule add <vault-repo-url> lib/research_style
```

Then in R scripts:

```r
source("lib/research_style/R/palettes.R")
source("lib/research_style/R/theme_research.R")
```
