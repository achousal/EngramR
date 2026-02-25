# test-palettes.R -- Tests for palettes.R color definitions and helpers

library(testthat)

# Source the module under test
source(file.path(dirname(dirname(testthat::test_path())), "palettes.R"))

# -- Semantic palette constants ------------------------------------------------

test_that("SEX_COLORS has correct keys and values", {
  expect_named(SEX_COLORS, c("Male", "Female"))
  expect_equal(SEX_COLORS[["Male"]], "#377EB8")
  expect_equal(SEX_COLORS[["Female"]], "#E41A1C")
})

test_that("DX_COLORS has correct keys and values", {
  expect_named(DX_COLORS, c("P-", "P+"))
  expect_equal(DX_COLORS[["P-"]], "#4DAF4A")
  expect_equal(DX_COLORS[["P+"]], "#E41A1C")
})

test_that("BINARY_COLORS has correct keys", {
  expect_named(BINARY_COLORS, c("Control", "Case"))
})

test_that("DIRECTION_COLORS has Up/Down/NS", {
  expect_named(DIRECTION_COLORS, c("Up", "Down", "NS"))
  expect_equal(DIRECTION_COLORS[["NS"]], "#999999")
})

test_that("SIG_COLORS has sig/not sig", {
  expect_named(SIG_COLORS, c("sig", "not sig"))
})

# -- No banned purple hues ----------------------------------------------------

# Banned purples: bright UI purples like purple1 (#9B30FF), #7B2D8E, etc.
# Allowed: Set1 muted purple #984EA3

banned_purple_pattern <- "^#(9B30FF|7B2D8E|800080|A020F0|BF40BF)"

test_that("No banned purple hues in any palette", {
  all_colors <- c(
    SEX_COLORS, DX_COLORS, BINARY_COLORS,
    DIRECTION_COLORS, SIG_COLORS,
    unlist(LAB_PALETTES)
  )
  for (hex in all_colors) {
    expect_false(
      grepl(banned_purple_pattern, hex, ignore.case = TRUE),
      info = paste("Banned purple found:", hex)
    )
  }
})

test_that("Set1 muted purple #984EA3 is permitted", {
  expect_true("#984EA3" %in% LAB_PALETTES[["elahi"]])
})

# -- Lab palettes --------------------------------------------------------------

test_that("LAB_PALETTES has all three labs", {
  expect_true(all(c("elahi", "chipuk", "kuang") %in% names(LAB_PALETTES)))
})

test_that("Each lab palette has 8 colors", {
  for (lab in names(LAB_PALETTES)) {
    expect_length(LAB_PALETTES[[lab]], 8)
  }
})

test_that("Kuang palette defaults to Elahi", {
  expect_equal(LAB_PALETTES[["kuang"]], LAB_PALETTES[["elahi"]])
})

test_that("All palette values are valid hex colors", {
  hex_pattern <- "^#[0-9A-Fa-f]{6}$"
  all_colors <- unlist(LAB_PALETTES)
  for (hex in all_colors) {
    expect_true(grepl(hex_pattern, hex), info = paste("Invalid hex:", hex))
  }
})

# -- lab_palette() helper ------------------------------------------------------

test_that("lab_palette returns correct palette", {
  expect_equal(lab_palette("elahi"), LAB_PALETTES[["elahi"]])
  expect_equal(lab_palette("Chipuk"), LAB_PALETTES[["chipuk"]])
})

test_that("lab_palette with n returns subset", {
  pal <- lab_palette("elahi", n = 3)
  expect_length(pal, 3)
  expect_equal(pal, LAB_PALETTES[["elahi"]][1:3])
})

test_that("lab_palette errors on unknown lab", {
  expect_error(lab_palette("unknown"), "Unknown lab")
})

test_that("lab_palette errors when n exceeds palette size", {
  expect_error(lab_palette("elahi", n = 20), "palette has only")
})
