"""Pure functions for building Obsidian note content.

Constructs YAML frontmatter + Markdown body for all note types used
in the co-scientist system. No I/O -- returns strings only.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import yaml


def _render_note(frontmatter: dict[str, Any], body: str) -> str:
    """Render frontmatter + body into a complete note string."""
    fm_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).rstrip()
    return f"---\n{fm_str}\n---\n\n{body}"


# -- Literature note ----------------------------------------------------------


def build_literature_note(
    *,
    title: str,
    doi: str = "",
    authors: list[str] | None = None,
    year: int | str = "",
    journal: str = "",
    abstract: str = "",
    tags: list[str] | None = None,
    today: date | None = None,
) -> str:
    """Build a literature note.

    Args:
        title: Paper title.
        doi: DOI identifier.
        authors: List of author names.
        year: Publication year.
        journal: Journal name.
        abstract: Paper abstract.
        tags: Additional tags.
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    d = today or date.today()
    fm = {
        "type": "literature",
        "title": title,
        "doi": doi,
        "authors": authors or [],
        "year": str(year),
        "journal": journal,
        "tags": ["literature"] + (tags or []),
        "status": "unread",
        "created": d.isoformat(),
    }
    body = f"""## Abstract
{abstract}

## Key Points
-

## Methods Notes


## Relevance


## Citations

"""
    return _render_note(fm, body)


# -- Hypothesis note -----------------------------------------------------------


def build_hypothesis_note(
    *,
    title: str,
    hyp_id: str,
    statement: str = "",
    mechanism: str = "",
    research_goal: str = "",
    tags: list[str] | None = None,
    today: date | None = None,
) -> str:
    """Build a hypothesis note with the full structured format.

    Args:
        title: Hypothesis title.
        hyp_id: Unique hypothesis ID.
        statement: Core hypothesis statement.
        mechanism: Mechanistic explanation.
        research_goal: Wiki-link to research goal note.
        tags: Additional tags.
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    d = today or date.today()
    fm = {
        "type": "hypothesis",
        "title": title,
        "id": hyp_id,
        "status": "proposed",
        "elo": 1200,
        "matches": 0,
        "wins": 0,
        "losses": 0,
        "generation": 1,
        "parents": [],
        "children": [],
        "research_goal": research_goal,
        "tags": ["hypothesis"] + (tags or []),
        "created": d.isoformat(),
        "updated": d.isoformat(),
        "review_scores": {
            "novelty": None,
            "correctness": None,
            "testability": None,
            "impact": None,
            "overall": None,
        },
        "review_flags": [],
        "linked_experiments": [],
        "linked_literature": [],
    }
    body = f"""## Statement
{statement}

## Mechanism
{mechanism}

## Literature Grounding


## Testable Predictions
- [ ]

## Proposed Experiments


## Assumptions
-

## Limitations & Risks


## Review History


## Evolution History

"""
    return _render_note(fm, body)


# -- Experiment note -----------------------------------------------------------


def build_experiment_note(
    *,
    title: str,
    hypothesis_link: str = "",
    parameters: dict[str, Any] | None = None,
    seed: int | None = None,
    objective: str = "",
    tags: list[str] | None = None,
    today: date | None = None,
) -> str:
    """Build an experiment logging note.

    Args:
        title: Experiment title.
        hypothesis_link: Wiki-link to hypothesis being tested.
        parameters: Experiment parameters dict.
        seed: Random seed used.
        objective: Experiment objective.
        tags: Additional tags.
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    d = today or date.today()
    fm = {
        "type": "experiment",
        "title": title,
        "hypothesis": hypothesis_link,
        "parameters": parameters or {},
        "seed": seed,
        "status": "planned",
        "artifacts": [],
        "tags": ["experiment"] + (tags or []),
        "created": d.isoformat(),
    }
    body = f"""## Objective
{objective}

## Parameters


## Environment


## Results


## Artifacts


## Interpretation


## Next Steps

"""
    return _render_note(fm, body)


# -- EDA report note -----------------------------------------------------------


def build_eda_report_note(
    *,
    title: str,
    dataset_path: str = "",
    n_rows: int = 0,
    n_cols: int = 0,
    redacted_columns: list[str] | None = None,
    summary: str = "",
    tags: list[str] | None = None,
    today: date | None = None,
) -> str:
    """Build an EDA report note.

    Args:
        title: Report title.
        dataset_path: Path to the dataset analyzed.
        n_rows: Number of rows.
        n_cols: Number of columns.
        redacted_columns: Columns auto-redacted for PII.
        summary: Summary of findings.
        tags: Additional tags.
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    d = today or date.today()
    fm = {
        "type": "eda-report",
        "title": title,
        "dataset": dataset_path,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "redacted_columns": redacted_columns or [],
        "tags": ["eda-report"] + (tags or []),
        "created": d.isoformat(),
    }
    body = f"""## Summary
{summary}

## Column Overview


## Missing Data


## Distributions


## Correlations


## Outliers


## Figures


## Run Metadata

"""
    return _render_note(fm, body)


# -- Research goal note --------------------------------------------------------


def build_research_goal_note(
    *,
    title: str,
    objective: str = "",
    constraints: list[str] | None = None,
    evaluation_criteria: list[str] | None = None,
    domain: str = "",
    tags: list[str] | None = None,
    today: date | None = None,
) -> str:
    """Build a research goal note.

    Args:
        title: Goal title.
        objective: Research objective.
        constraints: Constraints on hypothesis generation.
        evaluation_criteria: How hypotheses should be evaluated.
        domain: Scientific domain.
        tags: Additional tags.
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    d = today or date.today()
    fm = {
        "type": "research-goal",
        "title": title,
        "status": "active",
        "constraints": constraints or [],
        "evaluation_criteria": evaluation_criteria or [],
        "domain": domain,
        "tags": ["research-goal"] + (tags or []),
        "created": d.isoformat(),
    }
    body = f"""## Objective
{objective}

## Background


## Constraints


## Desired Properties


## Key Literature

"""
    return _render_note(fm, body)


# -- Tournament match note -----------------------------------------------------


def build_tournament_match_note(
    *,
    research_goal: str,
    hypothesis_a: str,
    hypothesis_b: str,
    winner: str = "",
    elo_change_a: float = 0,
    elo_change_b: float = 0,
    debate_summary: str = "",
    verdict: str = "",
    justification: str = "",
    mode: str = "local",
    today: date | None = None,
) -> str:
    """Build a tournament match log note.

    Args:
        research_goal: Wiki-link to the research goal.
        hypothesis_a: Wiki-link to hypothesis A.
        hypothesis_b: Wiki-link to hypothesis B.
        winner: ID or link of the winning hypothesis.
        elo_change_a: Elo delta for hypothesis A.
        elo_change_b: Elo delta for hypothesis B.
        debate_summary: Summary of the debate.
        verdict: Winner declaration.
        justification: Why the winner was chosen.
        mode: Tournament mode ("local" or "federated").
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    d = today or date.today()
    fm = {
        "type": "tournament-match",
        "date": d.isoformat(),
        "research_goal": research_goal,
        "hypothesis_a": hypothesis_a,
        "hypothesis_b": hypothesis_b,
        "winner": winner,
        "elo_change_a": elo_change_a,
        "elo_change_b": elo_change_b,
        "mode": mode,
    }
    body = f"""## Debate Summary
{debate_summary}

## Novelty Comparison


## Correctness


## Testability


## Impact


## Verdict
{verdict}

## Justification
{justification}

"""
    return _render_note(fm, body)


# -- Meta-review note ----------------------------------------------------------


def build_meta_review_note(
    *,
    research_goal: str,
    hypotheses_reviewed: int = 0,
    matches_analyzed: int = 0,
    recurring_weaknesses: str = "",
    key_literature: str = "",
    invalid_assumptions: str = "",
    winner_patterns: str = "",
    recommendations_generation: str = "",
    recommendations_evolution: str = "",
    today: date | None = None,
) -> str:
    """Build a meta-review synthesis note.

    Args:
        research_goal: Wiki-link to the research goal.
        hypotheses_reviewed: Number of hypotheses reviewed.
        matches_analyzed: Number of tournament matches analyzed.
        recurring_weaknesses: Common weakness patterns.
        key_literature: Frequently cited key papers.
        invalid_assumptions: Common invalid assumptions.
        winner_patterns: What makes winning hypotheses win.
        recommendations_generation: Advice for /generate.
        recommendations_evolution: Advice for /evolve.
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    d = today or date.today()
    fm = {
        "type": "meta-review",
        "date": d.isoformat(),
        "research_goal": research_goal,
        "hypotheses_reviewed": hypotheses_reviewed,
        "matches_analyzed": matches_analyzed,
    }
    body = f"""## Recurring Weaknesses
{recurring_weaknesses}

## Key Literature
{key_literature}

## Invalid Assumptions
{invalid_assumptions}

## Winner Patterns
{winner_patterns}

## Recommendations for Generation
{recommendations_generation}

## Recommendations for Evolution
{recommendations_evolution}

"""
    return _render_note(fm, body)


# -- Lab note ------------------------------------------------------------------


def build_lab_note(
    *,
    lab_slug: str,
    pi: str = "",
    institution: str = "",
    hpc_cluster: str = "",
    hpc_scheduler: str = "",
    research_focus: str = "",
    tags: list[str] | None = None,
    today: date | None = None,
) -> str:
    """Build a lab entity note.

    Args:
        lab_slug: Lowercase lab identifier (e.g. "elahi").
        pi: Principal investigator name.
        institution: Institution name.
        hpc_cluster: HPC cluster name (e.g. "Minerva").
        hpc_scheduler: HPC scheduler (e.g. "LSF", "SLURM").
        research_focus: 1-2 sentence research focus description.
        tags: Additional tags.
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    d = today or date.today()
    fm = {
        "type": "lab",
        "lab_slug": lab_slug,
        "pi": pi,
        "institution": institution,
        "hpc_cluster": hpc_cluster,
        "hpc_scheduler": hpc_scheduler,
        "research_focus": research_focus,
        "created": d.isoformat(),
        "updated": d.isoformat(),
        "tags": ["lab"] + (tags or []),
    }
    body = """## Projects

## Datasets

## Research Focus

## HPC Environment
"""
    return _render_note(fm, body)


# -- Project note --------------------------------------------------------------


def build_project_note(
    *,
    title: str,
    project_tag: str,
    lab: str,
    pi: str = "",
    status: str = "active",
    project_path: str,
    language: list[str] | None = None,
    hpc_path: str = "",
    scheduler: str = "LSF",
    linked_goals: list[str] | None = None,
    description: str = "",
    has_claude_md: bool = False,
    has_git: bool = False,
    has_tests: bool = False,
    tags: list[str] | None = None,
    today: date | None = None,
) -> str:
    """Build a project registry note.

    Args:
        title: Project title.
        project_tag: Slug for filtering (e.g. "celiac-risks").
        lab: Lab name.
        pi: Principal investigator name.
        status: Project status (active, maintenance, archived).
        project_path: Absolute path to project root.
        language: Programming languages used.
        hpc_path: HPC project path (e.g. /sc/arion/...).
        scheduler: HPC scheduler name.
        linked_goals: Wiki-links to research goals.
        description: Project description.
        has_claude_md: Whether project has a CLAUDE.md.
        has_git: Whether project has git initialized.
        has_tests: Whether project has tests.
        tags: Additional tags.
        today: Date override for testing.

    Returns:
        Complete note content string.
    """
    valid_statuses = {"active", "maintenance", "archived"}
    if status not in valid_statuses:
        msg = f"status must be one of {valid_statuses}, got {status!r}"
        raise ValueError(msg)

    d = today or date.today()
    fm = {
        "type": "project",
        "title": title,
        "project_tag": project_tag,
        "lab": lab,
        "pi": pi,
        "status": status,
        "project_path": project_path,
        "language": language or [],
        "hpc_path": hpc_path,
        "scheduler": scheduler,
        "linked_goals": linked_goals or [],
        "linked_hypotheses": [],
        "linked_experiments": [],
        "has_claude_md": has_claude_md,
        "has_git": has_git,
        "has_tests": has_tests,
        "created": d.isoformat(),
        "updated": d.isoformat(),
        "tags": ["project"] + (tags or []),
    }
    body = f"""## Description
{description}

## Research Goals

## Active Analyses

## Key Data

## HPC Notes

## Status Log
- {d.isoformat()}: Created
"""
    return _render_note(fm, body)
