"""Style showcase: generates one representative plot per builder + palette.

Run:
    cd _code && PYTHONPATH=src uv run python examples/style_showcase.py

Output saved to: _code/examples/gallery/
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd

from engram_r.plot_builders import (
    build_bar,
    build_box,
    build_forest,
    build_heatmap,
    build_roc,
    build_scatter,
    build_violin,
    build_volcano,
)
from engram_r.plot_stats import format_pval, run_correlation, run_test, select_test
from engram_r.plot_theme import (
    BINARY_COLORS,
    DIRECTION_COLORS,
    DX_COLORS,
    SEX_COLORS,
    apply_research_theme,
    get_lab_palette,
    save_figure,
)

OUT = Path(__file__).parent / "gallery"
OUT.mkdir(exist_ok=True)

# Output format: pass "pdf" for publication, "png" for quick review
FMT = sys.argv[1] if len(sys.argv) > 1 else "png"

rng = np.random.default_rng(42)

apply_research_theme()


# ---------------------------------------------------------------------------
# 1. Violin: Sex comparison (SEX_COLORS)
# ---------------------------------------------------------------------------
n = 80
df_sex = pd.DataFrame({
    "Sex": rng.choice(["Male", "Female"], n),
    "Biomarker (pg/mL)": np.concatenate([
        rng.normal(12, 3, n // 2),
        rng.normal(15, 3, n // 2),
    ]),
})
fig, ax = build_violin(
    df_sex, "Sex", "Biomarker (pg/mL)",
    palette=SEX_COLORS,
    title="Plasma Biomarker by Sex",
)
male = df_sex.loc[df_sex["Sex"] == "Male", "Biomarker (pg/mL)"]
female = df_sex.loc[df_sex["Sex"] == "Female", "Biomarker (pg/mL)"]
test = select_test("two_group", n_per_group=n // 2, normal=False)
res = run_test(male.values, female.values, test=test)
ax.text(
    0.5, 0.97, res.format(),
    transform=ax.transAxes, ha="center", va="top", fontsize=11,
)
save_figure(fig, OUT / "01_violin_sex", fmt=FMT,
            sidecar_text=f"Male vs Female\t{format_pval(res.pvalue)}\n")
print("  [1/10] Violin + SEX_COLORS")


# ---------------------------------------------------------------------------
# 2. Box: Diagnosis groups (DX_COLORS)
# ---------------------------------------------------------------------------
n = 100
df_dx = pd.DataFrame({
    "Diagnosis": rng.choice(["P-", "P+"], n),
    "Cognition Score": np.concatenate([
        rng.normal(28, 2, n // 2),
        rng.normal(24, 3, n // 2),
    ]),
})
fig, ax = build_box(
    df_dx, "Diagnosis", "Cognition Score",
    palette=DX_COLORS,
    title="Cognitive Score by Diagnosis",
)
save_figure(fig, OUT / "02_box_dx", fmt=FMT)
print("  [2/10] Box + DX_COLORS")


# ---------------------------------------------------------------------------
# 3. Box grouped: Diagnosis x Sex (DX + hue)
# ---------------------------------------------------------------------------
n = 120
df_grouped = pd.DataFrame({
    "Diagnosis": np.repeat(["P-", "P+"], n // 2),
    "Sex": np.tile(rng.choice(["Male", "Female"], n // 2), 2),
    "CSF Ab42": np.concatenate([
        rng.normal(1200, 200, n // 2),
        rng.normal(800, 250, n // 2),
    ]),
})
fig, ax = build_box(
    df_grouped, "Diagnosis", "CSF Ab42",
    hue="Sex", palette=SEX_COLORS,
    title="CSF Ab42 by Diagnosis and Sex",
)
save_figure(fig, OUT / "03_box_grouped_dx_sex", fmt=FMT)
print("  [3/10] Box grouped + SEX_COLORS x DX")


# ---------------------------------------------------------------------------
# 4. Scatter + regression: Biomarker correlation
# ---------------------------------------------------------------------------
n = 60
age = rng.uniform(55, 90, n)
biomarker = 0.4 * age + rng.normal(0, 5, n)
df_scatter = pd.DataFrame({
    "Age": age,
    "Plasma NfL (pg/mL)": biomarker,
})
fig, ax = build_scatter(
    df_scatter, "Age", "Plasma NfL (pg/mL)",
    add_lm=True,
    title="Plasma NfL vs Age",
)
corr = run_correlation(age, biomarker, method="spearman")
ax.text(
    0.02, 0.98, corr.format(),
    transform=ax.transAxes, ha="left", va="top", fontsize=11,
)
save_figure(fig, OUT / "04_scatter_correlation", fmt=FMT,
            sidecar_text=f"Age vs NfL\t{format_pval(corr.pvalue)}\n")
print("  [4/10] Scatter + regression")


# ---------------------------------------------------------------------------
# 5. Scatter colored by group (BINARY_COLORS)
# ---------------------------------------------------------------------------
n = 80
group = rng.choice(["Control", "Case"], n)
x_val = rng.normal(0, 1, n) + (group == "Case").astype(float) * 0.8
y_val = rng.normal(0, 1, n) + (group == "Case").astype(float) * 0.6
df_binary = pd.DataFrame({
    "PC1": x_val,
    "PC2": y_val,
    "Group": group,
})
fig, ax = build_scatter(
    df_binary, "PC1", "PC2",
    hue="Group", palette=BINARY_COLORS,
    title="PCA: Case vs Control",
)
save_figure(fig, OUT / "05_scatter_binary", fmt=FMT)
print("  [5/10] Scatter + BINARY_COLORS")


# ---------------------------------------------------------------------------
# 6. Heatmap: Correlation matrix (DIVERGING)
# ---------------------------------------------------------------------------
n = 50
features = ["Ab42", "pTau181", "NfL", "GFAP", "IL-6"]
data_mat = rng.normal(0, 1, (n, len(features)))
data_mat[:, 1] = data_mat[:, 0] * 0.7 + rng.normal(0, 0.5, n)
data_mat[:, 3] = data_mat[:, 2] * -0.5 + rng.normal(0, 0.5, n)
corr_mat = pd.DataFrame(data_mat, columns=features).corr()
fig, ax = build_heatmap(
    corr_mat,
    title="Biomarker Correlations",
    vmin=-1, vmax=1,
)
save_figure(fig, OUT / "06_heatmap_diverging", fmt=FMT)
print("  [6/10] Heatmap (diverging)")


# ---------------------------------------------------------------------------
# 7. Volcano: Differential expression (DIRECTION_COLORS)
# ---------------------------------------------------------------------------
n = 500
log2fc = rng.normal(0, 1.5, n)
pvals = 10 ** rng.uniform(-6, 0, n)
direction = np.where(
    (np.abs(log2fc) > 1) & (pvals < 0.05),
    np.where(log2fc > 0, "Up", "Down"),
    "NS",
)
df_volcano = pd.DataFrame({
    "log2FC": log2fc,
    "pvalue": pvals,
    "Direction": direction,
})
fig, ax = build_volcano(
    df_volcano, "log2FC", "pvalue",
    direction="Direction",
    title="Differential Expression: P+ vs P-",
)
n_up = (direction == "Up").sum()
n_down = (direction == "Down").sum()
ax.text(
    0.02, 0.98, f"Up: {n_up}  Down: {n_down}",
    transform=ax.transAxes, ha="left", va="top", fontsize=11,
)
save_figure(fig, OUT / "07_volcano_direction", fmt=FMT)
print("  [7/10] Volcano + DIRECTION_COLORS")


# ---------------------------------------------------------------------------
# 8. Forest: Effect sizes
# ---------------------------------------------------------------------------
labels = ["CSF Ab42", "CSF pTau", "Plasma NfL", "GFAP", "IL-6", "TNF-a"]
estimates = [0.82, 1.45, 0.55, 1.10, 0.30, -0.15]
ci_lo = [e - rng.uniform(0.2, 0.5) for e in estimates]
ci_hi = [e + rng.uniform(0.2, 0.5) for e in estimates]
df_forest = pd.DataFrame({
    "label": labels,
    "estimate": estimates,
    "ci_lower": ci_lo,
    "ci_upper": ci_hi,
})
fig, ax = build_forest(
    df_forest,
    title="Effect Sizes: Biomarker Associations",
)
save_figure(fig, OUT / "08_forest", fmt=FMT)
print("  [8/10] Forest plot")


# ---------------------------------------------------------------------------
# 9. ROC: Classification performance
# ---------------------------------------------------------------------------
n = 200
y_true = rng.integers(0, 2, n)
y_score = y_true * 0.6 + rng.normal(0, 0.4, n)
fig, ax = build_roc(
    y_true=y_true, y_score=y_score,
    title="ROC: AD Classification",
)
from sklearn.metrics import roc_auc_score

auc_val = roc_auc_score(y_true, y_score)
ax.text(
    0.6, 0.05, f"AUC = {auc_val:.3f}",
    transform=ax.transAxes, fontsize=13,
)
save_figure(fig, OUT / "09_roc", fmt=FMT)
print("  [9/10] ROC curve")


# ---------------------------------------------------------------------------
# 10. Bar: Group means with error bars (Lab palette)
# ---------------------------------------------------------------------------
groups = ["Ctrl", "Low", "Med", "High"]
means = [5.2, 7.1, 9.8, 12.3]
sems = [0.8, 1.0, 1.2, 0.9]
df_bar = pd.DataFrame({
    "Treatment": groups,
    "Expression": means,
    "SEM": sems,
})
lab_pal = get_lab_palette("elahi", n=4)
fig, ax = build_bar(
    df_bar, "Treatment", "Expression",
    yerr="SEM",
    palette=lab_pal,
    title="Gene Expression by Treatment (Elahi Lab)",
)
save_figure(fig, OUT / "10_bar_elahi", fmt=FMT)
print(" [10/10] Bar + Elahi Lab palette")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\nGallery saved to: {OUT.resolve()}")
print("Files:")
for f in sorted(OUT.glob(f"*.{FMT}")):
    print(f"  {f.name}")
