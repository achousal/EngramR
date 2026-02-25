############################################################
# Style Guide Example Plots
#
# Generates 4 figures using the exact AD_Chloe / DAC_CRF
# patterns with synthetic data. Demonstrates:
#   1. Violin + strip (Dx x Sex dodge, significance brackets,
#      italic n labels, mean dash, pvalue sidecar)
#   2. Box + strip (same structure, box specifics)
#   3. Scatter + regression (per-sex lines, 4-line annotation:
#      Male r/p/n, Female r/p/n, Fisher Z, Interaction p)
#   4. Bar + error bars (accent colors, n labels, stat box)
#
# Seed: 42 for reproducibility.
############################################################

library(ggplot2)
library(dplyr)
library(tidyr)
library(rstatix)
library(ggpubr)

# --- Source vault helpers ---------------------------------------------------

# Resolve script directory robustly (works with Rscript and source())
.script_dir <- tryCatch(
  dirname(normalizePath(sys.frame(1)$ofile)),
  error = function(e) {
    args <- commandArgs(trailingOnly = FALSE)
    file_arg <- grep("^--file=", args, value = TRUE)
    if (length(file_arg) > 0) {
      dirname(normalizePath(sub("^--file=", "", file_arg[1])))
    } else {
      normalizePath(".")
    }
  }
)

vault_r <- file.path(dirname(.script_dir), "R")
source(file.path(vault_r, "palettes.R"))
source(file.path(vault_r, "theme_research.R"))

# --- Output directory -------------------------------------------------------

out_dir <- file.path(.script_dir, "output")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# --- Synthetic data ---------------------------------------------------------

set.seed(42)
n_per_group <- 40
N <- n_per_group * 4  # total rows

synth <- expand.grid(
  Diagnosis = c("P-", "P+"),
  SexLabel  = c("Male", "Female"),
  stringsAsFactors = FALSE
) %>%
  slice(rep(1:n(), each = n_per_group)) %>%
  mutate(
    ID = seq_len(n()),
    # Biomarker higher in P+, slight sex difference
    Biomarker = case_when(
      Diagnosis == "P-" & SexLabel == "Male"   ~ rnorm(N, 4.5, 1.2),
      Diagnosis == "P-" & SexLabel == "Female" ~ rnorm(N, 5.0, 1.1),
      Diagnosis == "P+" & SexLabel == "Male"   ~ rnorm(N, 6.8, 1.4),
      Diagnosis == "P+" & SexLabel == "Female" ~ rnorm(N, 7.5, 1.3)
    ),
    # NFL predictor for scatter
    NFL = case_when(
      SexLabel == "Male"   ~ runif(N, 10, 80),
      SexLabel == "Female" ~ runif(N, 12, 75)
    ),
    # Outcome correlated with NFL (different slope by sex)
    Outcome = case_when(
      SexLabel == "Male"   ~ 0.08 * NFL + rnorm(N, 2, 1.5),
      SexLabel == "Female" ~ 0.12 * NFL + rnorm(N, 1.5, 1.5)
    )
  )

# --- Helpers (AD_Chloe patterns) -------------------------------------------

format_p <- function(p) {
  if (is.na(p)) return("")
  if (p < 0.001) return("p<0.001")
  paste0("p=", sprintf("%.3f", p))
}

get_sig_stars <- function(p) {
  dplyr::case_when(
    is.na(p)  ~ "",
    p < 0.001 ~ "***",
    p < 0.01  ~ "**",
    p < 0.05  ~ "*",
    TRUE      ~ ""
  )
}

fisher_z_test <- function(r1, n1, r2, n2) {
  z1 <- 0.5 * log((1 + r1) / (1 - r1))
  z2 <- 0.5 * log((1 + r2) / (1 - r2))
  se_diff <- sqrt(1 / (n1 - 3) + 1 / (n2 - 3))
  z_score <- (z1 - z2) / se_diff
  p_val <- 2 * pnorm(-abs(z_score))
  list(z = z_score, p = p_val)
}

scale_y_zero <- function(expand_mult = c(0, 0.05)) {
  scale_y_continuous(limits = c(0, NA),
                     expand = expansion(mult = expand_mult))
}

scale_y_auto <- function(expand_mult = c(0.02, 0.05)) {
  scale_y_continuous(expand = expansion(mult = expand_mult))
}

# --- Example 1: Violin + strip (Dx x Sex) ----------------------------------

message("Building violin example...")

x_ad_neg <- 1; x_ad_pos <- 2
x_male_off <- -0.175; x_female_off <- 0.175

# Significance tests
stat_dx <- synth %>%
  group_by(SexLabel) %>%
  t_test(Biomarker ~ Diagnosis) %>%
  add_significance() %>%
  mutate(
    xmin = ifelse(SexLabel == "Male",
                  x_ad_neg + x_male_off, x_ad_neg + x_female_off),
    xmax = ifelse(SexLabel == "Male",
                  x_ad_pos + x_male_off, x_ad_pos + x_female_off),
    y.position = ifelse(SexLabel == "Male", 11.5, 12.5)
  )

stat_sex <- synth %>%
  group_by(Diagnosis) %>%
  t_test(Biomarker ~ SexLabel) %>%
  add_significance() %>%
  mutate(
    xmin = ifelse(Diagnosis == "P-",
                  x_ad_neg + x_male_off, x_ad_pos + x_male_off),
    xmax = ifelse(Diagnosis == "P-",
                  x_ad_neg + x_female_off, x_ad_pos + x_female_off),
    y.position = ifelse(Diagnosis == "P-", 13.5, 14.5)
  )

n_labels <- synth %>%
  group_by(Diagnosis, SexLabel) %>%
  summarise(N = n(), .groups = "drop") %>%
  mutate(
    x = ifelse(Diagnosis == "P-", x_ad_neg, x_ad_pos) +
      ifelse(SexLabel == "Male", x_male_off, x_female_off),
    label = paste0("n=", N)
  )

p_violin <- ggplot(synth, aes(x = Diagnosis, y = Biomarker, fill = SexLabel)) +
  geom_violin(position = position_dodge(width = 0.7),
              trim = FALSE, alpha = 0.35, linewidth = 0.4) +
  geom_jitter(aes(colour = SexLabel),
              position = position_jitterdodge(jitter.width = 0.1,
                                              dodge.width = 0.7),
              size = 1.5, alpha = 0.6) +
  stat_summary(aes(group = SexLabel), fun = mean, geom = "point",
               shape = 95, position = position_dodge(width = 0.7),
               size = 6, colour = "black") +
  stat_pvalue_manual(stat_dx, label = "{p.signif}",
                     tip.length = 0.02, step.increase = 0.08,
                     hide.ns = FALSE) +
  stat_pvalue_manual(stat_sex, label = "{p.signif}",
                     tip.length = 0.02, step.increase = 0.08,
                     hide.ns = FALSE) +
  geom_text(data = n_labels, aes(x = x, y = 0, label = label),
            inherit.aes = FALSE, size = 3, vjust = 1.5,
            fontface = "italic") +
  labs(title = "Biomarker by Diagnosis and Sex (Example)",
       subtitle = "Synthetic data; Welch t-test brackets",
       x = "Diagnosis", y = "Biomarker (AU)", fill = "Sex") +
  scale_y_zero(expand_mult = c(0.05, 0.25)) +
  scale_fill_sex() +
  scale_color_sex() +
  theme_research() +
  guides(colour = "none")

ggsave(file.path(out_dir, "example_violin_dx_sex.pdf"),
       plot = p_violin, width = 8, height = 6)

# Pvalue sidecar
pval_df <- bind_rows(
  stat_dx %>% mutate(bracket = "Dx within sex"),
  stat_sex %>% mutate(bracket = "Sex within dx")
) %>%
  select(bracket, group1, group2, any_of("SexLabel"),
         any_of("Diagnosis"), n1, n2, statistic, p, p.signif)

writeLines(
  c("Biomarker Violin -- Statistical Comparisons (Welch t-test)",
    paste0("Generated: ", Sys.time()), "",
    capture.output(print(as.data.frame(pval_df), row.names = FALSE))),
  file.path(out_dir, "example_violin_dx_sex_pvalues.txt")
)

message("  -> example_violin_dx_sex.pdf + _pvalues.txt")

# --- Example 2: Box + strip (Dx x Sex) -------------------------------------

message("Building box example...")

p_box <- ggplot(synth, aes(x = Diagnosis, y = Biomarker, fill = SexLabel)) +
  geom_boxplot(position = position_dodge(width = 0.7),
               width = 0.35, outlier.shape = NA,
               alpha = 0.35, linewidth = 0.6) +
  geom_jitter(aes(colour = SexLabel),
              position = position_jitterdodge(jitter.width = 0.1,
                                              dodge.width = 0.7),
              size = 1.5, alpha = 0.6) +
  stat_summary(aes(group = SexLabel), fun = mean, geom = "point",
               shape = 95, position = position_dodge(width = 0.7),
               size = 6, colour = "black") +
  stat_pvalue_manual(stat_dx, label = "{p.signif}",
                     tip.length = 0.02, step.increase = 0.08,
                     hide.ns = FALSE) +
  stat_pvalue_manual(stat_sex, label = "{p.signif}",
                     tip.length = 0.02, step.increase = 0.08,
                     hide.ns = FALSE) +
  geom_text(data = n_labels, aes(x = x, y = 0, label = label),
            inherit.aes = FALSE, size = 3, vjust = -0.3,
            fontface = "italic") +
  labs(title = "Biomarker by Diagnosis and Sex (Example)",
       subtitle = "Synthetic data; Welch t-test brackets",
       x = "Diagnosis", y = "Biomarker (AU)", fill = "Sex") +
  scale_y_zero(expand_mult = c(0, 0.10)) +
  scale_fill_sex() +
  scale_color_sex() +
  theme_research() +
  guides(colour = "none")

ggsave(file.path(out_dir, "example_box_dx_sex.pdf"),
       plot = p_box, width = 8, height = 6)
message("  -> example_box_dx_sex.pdf")

# --- Example 3: Scatter + regression (per-sex, 4-line annotation) ----------

message("Building scatter example...")

# Pearson correlations by sex
cor_stats <- synth %>%
  group_by(SexLabel) %>%
  summarise(
    N = n(),
    r = cor(NFL, Outcome, use = "complete.obs"),
    p_value = cor.test(NFL, Outcome)$p.value,
    .groups = "drop"
  )

# Fisher Z
fz <- fisher_z_test(
  cor_stats$r[cor_stats$SexLabel == "Male"],
  cor_stats$N[cor_stats$SexLabel == "Male"],
  cor_stats$r[cor_stats$SexLabel == "Female"],
  cor_stats$N[cor_stats$SexLabel == "Female"]
)

# Interaction
inter_fit <- lm(Outcome ~ NFL * SexLabel, data = synth)
inter_coefs <- summary(inter_fit)$coefficients
inter_p <- inter_coefs[grep("NFL:SexLabel", rownames(inter_coefs)),
                       "Pr(>|t|)"]

# 4-line annotation
male_row <- cor_stats %>% filter(SexLabel == "Male")
female_row <- cor_stats %>% filter(SexLabel == "Female")

annotation_text <- paste(
  sprintf("Male: r=%.2f, %s, n=%d", male_row$r,
          format_p(male_row$p_value), male_row$N),
  sprintf("Female: r=%.2f, %s, n=%d", female_row$r,
          format_p(female_row$p_value), female_row$N),
  sprintf("Fisher Z: z=%.2f, %s", fz$z, format_p(fz$p)),
  sprintf("Interaction: %s", format_p(inter_p)),
  sep = "\n"
)

p_scatter <- ggplot(synth, aes(x = NFL, y = Outcome,
                                colour = SexLabel, fill = SexLabel)) +
  geom_point(alpha = 0.6, size = 2.5,
             shape = 21, stroke = 0.5) +
  geom_smooth(method = "lm", se = TRUE,
              linewidth = 0.8, alpha = 0.18) +
  geom_label(data = data.frame(NFL = Inf, Outcome = Inf, label = annotation_text),
             aes(label = label), x = Inf, y = Inf,
             hjust = 1, vjust = 1, size = 2.5,
             colour = "grey30", fill = "white",
             label.padding = unit(0.3, "lines"),
             linewidth = 0.3,
             inherit.aes = FALSE) +
  labs(title = "NFL vs Outcome by Sex (Example)",
       subtitle = "Synthetic data; Pearson correlation + Fisher Z comparison",
       x = "NFL Concentration", y = "Outcome Measure",
       colour = "Sex", fill = "Sex") +
  scale_y_auto() +
  scale_color_sex() +
  scale_fill_sex() +
  theme_research() +
  guides(fill = "none")

ggsave(file.path(out_dir, "example_scatter_by_sex.pdf"),
       plot = p_scatter, width = 10, height = 6)
message("  -> example_scatter_by_sex.pdf")

# --- Example 4: Bar + accent colors + stat box -----------------------------

message("Building bar example...")

# Accent colors (Elahi first-choice)
ACCENT_PRIMARY   <- "#9B30FF"  # purple1
ACCENT_SECONDARY <- "#FFA500"  # orange1
ACCENT_TERTIARY  <- "#90EE90"  # lightgreen

bar_data <- data.frame(
  Group = factor(c("Low", "Mid", "High"), levels = c("Low", "Mid", "High")),
  Mean  = c(4.2, 6.5, 8.1),
  SE    = c(0.5, 0.7, 0.6),
  N     = c(48, 52, 45)
)

# Kruskal-Wallis on synthetic grouped data
kw_data <- synth %>%
  mutate(Tertile = case_when(
    Biomarker < quantile(Biomarker, 1/3) ~ "Low",
    Biomarker < quantile(Biomarker, 2/3) ~ "Mid",
    TRUE ~ "High"
  ))
kw_test <- kruskal.test(Outcome ~ Tertile, data = kw_data)

stat_text <- paste0(
  "Kruskal-Wallis H = ", sprintf("%.1f", kw_test$statistic), "\n",
  format_p(kw_test$p.value)
)

p_bar <- ggplot(bar_data, aes(x = Group, y = Mean, fill = Group)) +
  geom_col(alpha = 0.85, colour = "black", linewidth = 0.6, width = 0.7) +
  geom_errorbar(aes(ymin = Mean - SE, ymax = Mean + SE),
                width = 0.2, linewidth = 1.0) +
  geom_text(aes(y = 0, label = paste0("n=", N)),
            vjust = 1.5, size = 3, fontface = "italic") +
  scale_fill_manual(values = c("Low"  = ACCENT_TERTIARY,
                                "Mid"  = ACCENT_SECONDARY,
                                "High" = ACCENT_PRIMARY)) +
  annotate("label", x = 3, y = max(bar_data$Mean + bar_data$SE) + 0.3,
           label = stat_text, hjust = 1, vjust = 0,
           size = 3, fill = "wheat", alpha = 0.8,
           label.padding = unit(0.3, "lines"),
           label.r = unit(0.15, "lines")) +
  labs(title = "Elahi Accent Colors -- Bar + Error Bars",
       subtitle = "Synthetic data; Kruskal-Wallis test",
       x = NULL, y = "Measurement (AU)") +
  scale_y_zero(expand_mult = c(0.05, 0.15)) +
  theme_research() +
  theme(legend.position = "none")

ggsave(file.path(out_dir, "example_bar_accent.pdf"),
       plot = p_bar, width = 7, height = 5)
message("  -> example_bar_accent.pdf")

message("\nAll examples saved to: ", out_dir)
