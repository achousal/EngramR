"""Tests for note builder functions."""

from datetime import date

import yaml

import pytest

from engram_r.note_builder import (
    build_eda_report_note,
    build_experiment_note,
    build_hypothesis_note,
    build_lab_note,
    build_literature_note,
    build_meta_review_note,
    build_project_note,
    build_research_goal_note,
    build_tournament_match_note,
)


def _parse_frontmatter(content: str) -> dict:
    """Extract and parse YAML frontmatter from note content."""
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Missing frontmatter delimiters"
    return yaml.safe_load(parts[1])


class TestBuildLiteratureNote:
    def test_basic_structure(self):
        note = build_literature_note(
            title="Test Paper",
            doi="10.1234/test",
            authors=["Smith A", "Jones B"],
            year=2024,
            journal="Nature",
            abstract="An abstract.",
            today=date(2026, 2, 21),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "literature"
        assert fm["title"] == "Test Paper"
        assert fm["doi"] == "10.1234/test"
        assert fm["status"] == "unread"
        assert "## Abstract" in note
        assert "An abstract." in note

    def test_defaults(self):
        note = build_literature_note(title="Minimal")
        fm = _parse_frontmatter(note)
        assert fm["authors"] == []
        assert "literature" in fm["tags"]


class TestBuildHypothesisNote:
    def test_full_structure(self):
        note = build_hypothesis_note(
            title="Test Hyp",
            hyp_id="hyp-001",
            statement="A bold claim.",
            mechanism="Via pathway X.",
            research_goal="[[goal-1]]",
            today=date(2026, 2, 21),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "hypothesis"
        assert fm["id"] == "hyp-001"
        assert fm["elo"] == 1200
        assert fm["generation"] == 1
        assert fm["review_scores"]["novelty"] is None
        assert "## Statement" in note
        assert "A bold claim." in note
        assert "## Mechanism" in note
        assert "## Review History" in note
        assert "## Evolution History" in note

    def test_defaults(self):
        note = build_hypothesis_note(title="T", hyp_id="h1")
        fm = _parse_frontmatter(note)
        assert fm["parents"] == []
        assert fm["children"] == []


class TestBuildExperimentNote:
    def test_structure(self):
        note = build_experiment_note(
            title="Exp 1",
            hypothesis_link="[[hyp-001]]",
            parameters={"alpha": 0.05, "n_iter": 1000},
            seed=42,
            objective="Test the thing.",
            today=date(2026, 2, 21),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "experiment"
        assert fm["seed"] == 42
        assert fm["parameters"]["alpha"] == 0.05
        assert "## Objective" in note


class TestBuildEdaReportNote:
    def test_structure(self):
        note = build_eda_report_note(
            title="EDA 1",
            dataset_path="/data/cohort.csv",
            n_rows=100,
            n_cols=12,
            redacted_columns=["SubjectID"],
            today=date(2026, 2, 21),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "eda-report"
        assert fm["n_rows"] == 100
        assert "SubjectID" in fm["redacted_columns"]
        assert "## Distributions" in note


class TestBuildResearchGoalNote:
    def test_structure(self):
        note = build_research_goal_note(
            title="AD Biomarkers",
            objective="Identify novel biomarker relationships.",
            domain="neurodegeneration",
            today=date(2026, 2, 21),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "research-goal"
        assert fm["status"] == "active"
        assert fm["domain"] == "neurodegeneration"
        assert "## Objective" in note


class TestBuildTournamentMatchNote:
    def test_structure(self):
        note = build_tournament_match_note(
            research_goal="[[goal-1]]",
            hypothesis_a="[[hyp-001]]",
            hypothesis_b="[[hyp-002]]",
            winner="hyp-001",
            elo_change_a=16.0,
            elo_change_b=-16.0,
            debate_summary="A was more novel.",
            verdict="Hypothesis A wins.",
            justification="Stronger literature grounding.",
            today=date(2026, 2, 21),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "tournament-match"
        assert fm["winner"] == "hyp-001"
        assert fm["elo_change_a"] == 16.0
        assert "## Verdict" in note


class TestBuildMetaReviewNote:
    def test_structure(self):
        note = build_meta_review_note(
            research_goal="[[goal-1]]",
            hypotheses_reviewed=10,
            matches_analyzed=15,
            recurring_weaknesses="Weak literature grounding.",
            today=date(2026, 2, 21),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "meta-review"
        assert fm["hypotheses_reviewed"] == 10
        assert "## Recurring Weaknesses" in note
        assert "Weak literature grounding." in note


class TestBuildLabNote:
    def test_basic_structure(self):
        note = build_lab_note(
            lab_slug="elahi",
            pi="Fanny Elahi",
            institution="Mount Sinai",
            hpc_cluster="Minerva",
            hpc_scheduler="LSF",
            research_focus="Neurodegeneration biomarker discovery",
            today=date(2026, 2, 23),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "lab"
        assert fm["lab_slug"] == "elahi"
        assert fm["pi"] == "Fanny Elahi"
        assert fm["institution"] == "Mount Sinai"
        assert fm["hpc_cluster"] == "Minerva"
        assert fm["hpc_scheduler"] == "LSF"
        assert fm["created"] == "2026-02-23"
        assert fm["updated"] == "2026-02-23"
        assert "lab" in fm["tags"]
        assert "## Projects" in note
        assert "## Datasets" in note

    def test_defaults(self):
        note = build_lab_note(lab_slug="test")
        fm = _parse_frontmatter(note)
        assert fm["pi"] == ""
        assert fm["institution"] == ""
        assert fm["hpc_cluster"] == ""
        assert fm["hpc_scheduler"] == ""
        assert fm["research_focus"] == ""
        assert "lab" in fm["tags"]

    def test_custom_tags(self):
        note = build_lab_note(lab_slug="test", tags=["custom"])
        fm = _parse_frontmatter(note)
        assert "lab" in fm["tags"]
        assert "custom" in fm["tags"]


class TestBuildProjectNote:
    def test_basic_structure(self):
        note = build_project_note(
            title="CeliacRisks",
            project_tag="celiac-risks",
            lab="Elahi",
            pi="Elahi",
            project_path="/Users/test/Projects/CeliacRisks",
            language=["Python", "Bash"],
            hpc_path="/sc/arion/projects/test",
            description="ML pipeline for CeD risk prediction.",
            has_claude_md=True,
            has_git=True,
            has_tests=True,
            tags=["elahi-lab"],
            today=date(2026, 2, 21),
        )
        fm = _parse_frontmatter(note)
        assert fm["type"] == "project"
        assert fm["title"] == "CeliacRisks"
        assert fm["project_tag"] == "celiac-risks"
        assert fm["lab"] == "Elahi"
        assert fm["pi"] == "Elahi"
        assert fm["status"] == "active"
        assert fm["project_path"] == "/Users/test/Projects/CeliacRisks"
        assert fm["language"] == ["Python", "Bash"]
        assert fm["hpc_path"] == "/sc/arion/projects/test"
        assert fm["has_claude_md"] is True
        assert fm["has_git"] is True
        assert fm["has_tests"] is True
        assert fm["created"] == "2026-02-21"
        assert fm["updated"] == "2026-02-21"
        assert "project" in fm["tags"]
        assert "elahi-lab" in fm["tags"]
        assert "## Description" in note
        assert "ML pipeline for CeD risk prediction." in note
        assert "## Research Goals" in note
        assert "## Status Log" in note

    def test_valid_statuses(self):
        for status in ("active", "maintenance", "archived"):
            note = build_project_note(
                title="T",
                project_tag="t",
                lab="L",
                project_path="/tmp/t",
                status=status,
                today=date(2026, 2, 21),
            )
            fm = _parse_frontmatter(note)
            assert fm["status"] == status

        with pytest.raises(ValueError, match="status must be one of"):
            build_project_note(
                title="T",
                project_tag="t",
                lab="L",
                project_path="/tmp/t",
                status="invalid",
            )

    def test_defaults(self):
        note = build_project_note(
            title="Minimal",
            project_tag="minimal",
            lab="Test",
            project_path="/tmp/minimal",
        )
        fm = _parse_frontmatter(note)
        assert fm["pi"] == ""
        assert fm["status"] == "active"
        assert fm["language"] == []
        assert fm["hpc_path"] == ""
        assert fm["scheduler"] == "LSF"
        assert fm["linked_goals"] == []
        assert fm["linked_hypotheses"] == []
        assert fm["linked_experiments"] == []
        assert fm["has_claude_md"] is False
        assert fm["has_git"] is False
        assert fm["has_tests"] is False
        assert "project" in fm["tags"]


# ---------------------------------------------------------------------------
# YAML safety: colon-containing values via yaml.dump (regression)
# ---------------------------------------------------------------------------


class TestYAMLSafetyInNoteBuilder:
    """Confirm _render_note (via yaml.dump) safely handles special characters."""

    def test_colon_in_title_is_quoted(self):
        """yaml.dump auto-quotes strings containing colons."""
        note = build_literature_note(
            title="docs: tighten am/pm references",
            doi="10.1234/test",
            today=date(2026, 2, 22),
        )
        fm = _parse_frontmatter(note)
        assert fm["title"] == "docs: tighten am/pm references"

    def test_colon_in_description(self):
        """Experiment objective with colons roundtrips safely."""
        note = build_experiment_note(
            title="Test",
            objective="Step 1: load data. Step 2: run analysis.",
            today=date(2026, 2, 22),
        )
        fm = _parse_frontmatter(note)
        assert "Step 1:" in note

    def test_brackets_in_research_goal(self):
        """Brackets in string values do not become YAML lists."""
        note = build_research_goal_note(
            title="[Draft] AD Biomarkers",
            objective="Identify markers.",
            today=date(2026, 2, 22),
        )
        fm = _parse_frontmatter(note)
        assert fm["title"] == "[Draft] AD Biomarkers"


class TestTournamentMatchMode:
    """Tournament match note mode parameter for federated tournaments."""

    def test_default_mode_is_local(self):
        note = build_tournament_match_note(
            research_goal="[[goal-1]]",
            hypothesis_a="[[hyp-001]]",
            hypothesis_b="[[hyp-002]]",
            today=date(2026, 2, 23),
        )
        fm = _parse_frontmatter(note)
        assert fm["mode"] == "local"

    def test_federated_mode(self):
        note = build_tournament_match_note(
            research_goal="[[goal-1]]",
            hypothesis_a="[[hyp-001]]",
            hypothesis_b="[[hyp-peer-001]]",
            mode="federated",
            today=date(2026, 2, 23),
        )
        fm = _parse_frontmatter(note)
        assert fm["mode"] == "federated"
