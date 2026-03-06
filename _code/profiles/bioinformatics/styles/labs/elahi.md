# Elahi Lab Visual Identity

Color palette, branding, and policies for all Elahi lab projects. Inherits format conventions from `styles/formats/`. Color values defined in `palettes/elahi.yaml`.

## First-choice accent colors

When a plot needs one, two, or three colors and no semantic mapping applies, reach for these in order:

| Rank | Color | R name | Hex |
|------|-------|--------|-----|
| Primary | purple | `purple1` | `#9B30FF` |
| Secondary | orange | `orange1` | `#FFA500` |
| Tertiary | light green | `lightgreen` | `#90EE90` |

## Categorical palette

ColorBrewer Set1 (8 colors). Used for categorical variables with more than three levels or when a dedicated semantic mapping applies.

| Position | Color | Hex | Common use |
|----------|-------|-----|------------|
| 1 | red | `#E41A1C` | |
| 2 | blue | `#377EB8` | |
| 3 | green | `#4DAF4A` | |
| 4 | muted purple | `#984EA3` | |
| 5 | orange | `#FF7F00` | |
| 6 | brown | `#A65628` | |
| 7 | pink | `#F781BF` | |
| 8 | grey | `#999999` | |

Access: `lab_palette("elahi")` (R) or `get_lab_palette("elahi")` (Python).

## Semantic mappings

| Mapping | Category | Hex | Scale helpers |
|---------|----------|-----|---------------|
| Sex | Male | `#377EB8` (blue) | `scale_color_sex()`, `scale_fill_sex()` |
| Sex | Female | `#E41A1C` (red) | |
| Diagnosis | P- | `#4DAF4A` (green) | `scale_color_dx()`, `scale_fill_dx()` |
| Diagnosis | P+ | `#E41A1C` (red) | |
| Binary | Control | `#4DAF4A` (green) | |
| Binary | Case | `#E41A1C` (red) | |

Red signals "attention" (female, positive diagnosis, case); blue/green signals "baseline" (male, negative diagnosis, control).

## Heatmap palettes

- **Diverging** (centered at 0): `RdBu` / `RdBu_r`
- **Sequential** (density/counts): `Blues`

## Dashboard branding

| Field | Value |
|-------|-------|
| Title | Biomarker Report |
| Institution | Elahi Lab |
| Disclaimer | For research use only. Not for clinical diagnostic purposes. |
| Footer | Elahi Lab -- Icahn School of Medicine at Mount Sinai |
