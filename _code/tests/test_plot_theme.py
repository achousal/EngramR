"""Tests for engram_r.plot_theme -- theme constants, palettes, and helpers."""

from __future__ import annotations

import re

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")  # non-interactive backend for CI

from engram_r.plot_theme import (
    BINARY_COLORS,
    DIRECTION_COLORS,
    DIVERGING_PALETTE,
    DX_COLORS,
    FIGURE_SIZES,
    LAB_PALETTES,
    SEMANTIC_PALETTES,
    SEQUENTIAL_PALETTE,
    SEX_COLORS,
    SIG_COLORS,
    apply_research_theme,
    get_figure_size,
    get_lab_palette,
    load_palettes,
    save_figure,
)

# -- Color constants -----------------------------------------------------------


class TestSemanticPalettes:
    """Verify all semantic palettes have correct keys and hex values."""

    HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

    def test_sex_colors_keys(self):
        assert set(SEX_COLORS.keys()) == {"Male", "Female"}

    def test_dx_colors_keys(self):
        assert set(DX_COLORS.keys()) == {"P-", "P+"}

    def test_binary_colors_keys(self):
        assert set(BINARY_COLORS.keys()) == {"Control", "Case"}

    def test_direction_colors_keys(self):
        assert set(DIRECTION_COLORS.keys()) == {"Up", "Down", "NS"}

    def test_sig_colors_keys(self):
        assert set(SIG_COLORS.keys()) == {"sig", "not sig"}

    def test_semantic_palettes_dict(self):
        assert "sex" in SEMANTIC_PALETTES
        assert "dx" in SEMANTIC_PALETTES
        assert SEMANTIC_PALETTES["sex"] is SEX_COLORS

    def test_all_hex_valid(self):
        all_colors = [
            *SEX_COLORS.values(),
            *DX_COLORS.values(),
            *BINARY_COLORS.values(),
            *DIRECTION_COLORS.values(),
            *SIG_COLORS.values(),
        ]
        for color in all_colors:
            assert self.HEX_PATTERN.match(color), f"Invalid hex: {color}"

    def test_no_banned_purples(self):
        banned = {"#9B30FF", "#7B2D8E", "#800080", "#A020F0", "#BF40BF"}
        all_colors = set()
        for palette in [SEX_COLORS, DX_COLORS, BINARY_COLORS,
                        DIRECTION_COLORS, SIG_COLORS]:
            all_colors.update(palette.values())
        for pal in LAB_PALETTES.values():
            all_colors.update(pal)
        assert not all_colors & banned, "Banned purple hues found"

    def test_set1_muted_purple_permitted(self):
        assert "#984EA3" in LAB_PALETTES["elahi"]


class TestDivergingSequential:
    def test_diverging_is_rdbu(self):
        assert "RdBu" in DIVERGING_PALETTE

    def test_sequential_is_blues(self):
        assert SEQUENTIAL_PALETTE == "Blues"


# -- Lab palettes --------------------------------------------------------------


class TestLabPalettes:
    def test_all_labs_present(self):
        assert {"elahi", "chipuk", "kuang"} <= set(LAB_PALETTES.keys())

    def test_each_has_eight_colors(self):
        for lab, pal in LAB_PALETTES.items():
            assert len(pal) == 8, f"{lab} has {len(pal)} colors"

    def test_kuang_defaults_to_elahi(self):
        assert LAB_PALETTES["kuang"] == LAB_PALETTES["elahi"]


class TestLoadPalettes:
    """Test YAML loading with fallback behavior."""

    def test_loads_from_yaml(self, tmp_path):
        yaml_content = """
semantic:
  sex:
    Male: "#AABBCC"
    Female: "#DDEEFF"
labs:
  test_lab:
    - "#111111"
    - "#222222"
    - "#333333"
    - "#444444"
    - "#555555"
    - "#666666"
    - "#777777"
    - "#888888"
diverging: "coolwarm"
sequential: "Greens"
"""
        yaml_file = tmp_path / "palettes.yaml"
        yaml_file.write_text(yaml_content)
        result = load_palettes(yaml_file)
        assert result["semantic"]["sex"]["Male"] == "#AABBCC"
        assert result["labs"]["test_lab"][0] == "#111111"
        assert result["diverging"] == "coolwarm"
        assert result["sequential"] == "Greens"

    def test_fallback_on_missing_file(self):
        from pathlib import Path
        result = load_palettes(Path("/nonexistent/palettes.yaml"))
        assert "semantic" in result
        assert "labs" in result
        assert "elahi" in result["labs"]
        assert result["diverging"] == "RdBu_r"

    def test_fallback_on_invalid_yaml(self, tmp_path):
        yaml_file = tmp_path / "palettes.yaml"
        yaml_file.write_text(": :\n  - [")
        result = load_palettes(yaml_file)
        assert "elahi" in result["labs"]


class TestGetLabPalette:
    def test_returns_full_palette(self):
        pal = get_lab_palette("elahi")
        assert len(pal) == 8

    def test_case_insensitive(self):
        assert get_lab_palette("Chipuk") == get_lab_palette("chipuk")

    def test_subset(self):
        pal = get_lab_palette("elahi", n=3)
        assert len(pal) == 3
        assert pal == LAB_PALETTES["elahi"][:3]

    def test_unknown_lab_raises(self):
        with pytest.raises(ValueError, match="Unknown lab"):
            get_lab_palette("unknown")

    def test_n_too_large_raises(self):
        with pytest.raises(ValueError, match="palette has only"):
            get_lab_palette("elahi", n=20)


# -- Figure sizes --------------------------------------------------------------


class TestFigureSizes:
    def test_all_expected_types(self):
        expected = {
            "box_grouped", "box_single", "violin_grouped", "violin_single",
            "scatter_multi", "scatter_single", "scatter_bivar",
            "heatmap", "forest", "volcano", "roc", "bar",
        }
        assert expected <= set(FIGURE_SIZES.keys())

    def test_all_tuples_of_two(self):
        for key, size in FIGURE_SIZES.items():
            assert len(size) == 2, f"{key} size has {len(size)} elements"
            assert all(s > 0 for s in size), f"{key} has non-positive dim"


class TestGetFigureSize:
    def test_known_type(self):
        w, h = get_figure_size("roc")
        assert w == 7
        assert h == 7

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown plot type"):
            get_figure_size("nonexistent")


# -- Theme application --------------------------------------------------------


class TestApplyResearchTheme:
    def test_applies_without_error(self):
        apply_research_theme()

    def test_custom_font_size(self):
        apply_research_theme(font_size=18)
        assert matplotlib.rcParams["font.size"] == 18

    def test_sets_300_dpi_for_save(self):
        apply_research_theme()
        assert matplotlib.rcParams["savefig.dpi"] == 300

    def test_disables_grid(self):
        apply_research_theme()
        assert matplotlib.rcParams["axes.grid"] is False

    def test_removes_top_right_spines(self):
        apply_research_theme()
        assert matplotlib.rcParams["axes.spines.top"] is False
        assert matplotlib.rcParams["axes.spines.right"] is False


# -- save_figure ---------------------------------------------------------------


class TestSaveFigure:
    def test_saves_pdf(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = save_figure(fig, tmp_path / "test_fig", fmt="pdf")
        assert path.exists()
        assert path.suffix == ".pdf"

    def test_saves_png(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = save_figure(fig, tmp_path / "test_fig", fmt="png")
        assert path.exists()
        assert path.suffix == ".png"

    def test_sidecar_text(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = save_figure(
            fig, tmp_path / "test_fig", fmt="pdf",
            sidecar_text="Group A\tp = 0.042\n"
        )
        sidecar = path.with_name("test_fig_pvalues.txt")
        assert sidecar.exists()
        assert "p = 0.042" in sidecar.read_text()

    def test_creates_parent_dirs(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        nested = tmp_path / "a" / "b" / "c" / "fig"
        path = save_figure(fig, nested, fmt="pdf")
        assert path.exists()

    def test_appends_extension_if_missing(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = save_figure(fig, tmp_path / "no_ext", fmt="svg")
        assert path.suffix == ".svg"

    def test_respects_existing_extension(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        path = save_figure(fig, tmp_path / "has_ext.pdf", fmt="pdf")
        assert path.suffix == ".pdf"
