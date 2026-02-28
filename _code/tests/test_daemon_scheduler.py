"""Tests for daemon scheduler -- priority cascade, cycle detection, task selection."""

import json
import textwrap

import pytest
import yaml

from engram_r.daemon_config import (
    DaemonConfig,
    MetabolicConfig,
    ScheduleEntry,
    load_config,
)
from engram_r.daemon_scheduler import (
    DaemonTask,
    FailedCategory,
    GoalState,
    RootCause,
    TaskStackItem,
    VaultState,
    _check_p1,
    _check_p1_experiments_only,
    _check_p2,
    _check_p2_5,
    _check_p3,
    _check_p3_5,
    _check_schedules,
    _count_orphan_notes,
    _default_vault_path,
    _extract_root_causes,
    _goal_slug,
    _read_frontmatter,
    _slugify,
    build_health_fix_task,
    build_health_observation,
    build_inbox_entries,
    build_tier3_entries,
    create_health_observations,
    get_latest_health_report,
    parse_health_report,
    parse_task_stack,
    scan_vault,
    select_task,
)
from engram_r.metabolic_indicators import MetabolicState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config():
    return DaemonConfig(
        goals_priority=[
            "goal-ad-biomarkers",
            "dynamic-biomarker-networks-ad",
            "lps-neuroinflammation-fcg",
        ]
    )


@pytest.fixture
def idle_state():
    """A vault with no work to do (cycle_stale -- no new hypotheses)."""
    return VaultState(
        goals=[
            GoalState(
                goal_id="goal-ad-biomarkers",
                hypothesis_count=12,
                undermatched_count=0,
                latest_tournament_mtime=100.0,
                latest_meta_review_mtime=200.0,
                latest_landscape_mtime=300.0,
                latest_hypothesis_mtime=50.0,
            ),
        ],
    )


@pytest.fixture
def vault_needing_tournament():
    return VaultState(
        goals=[
            GoalState(
                goal_id="goal-ad-biomarkers",
                hypothesis_count=12,
                undermatched_count=4,
                latest_tournament_mtime=100.0,
                latest_meta_review_mtime=200.0,
                latest_landscape_mtime=300.0,
            ),
        ],
    )


@pytest.fixture
def vault_needing_meta_review():
    return VaultState(
        goals=[
            GoalState(
                goal_id="goal-ad-biomarkers",
                hypothesis_count=12,
                undermatched_count=0,
                latest_tournament_mtime=500.0,
                latest_meta_review_mtime=200.0,
                latest_landscape_mtime=300.0,
            ),
        ],
    )


@pytest.fixture
def vault_needing_landscape():
    return VaultState(
        goals=[
            GoalState(
                goal_id="goal-ad-biomarkers",
                hypothesis_count=12,
                undermatched_count=0,
                latest_tournament_mtime=100.0,
                latest_meta_review_mtime=500.0,
                latest_landscape_mtime=300.0,
            ),
        ],
    )


SAMPLE_HEALTH_REPORT = textwrap.dedent("""\
    === HEALTH REPORT ===
    Mode: quick
    Date: 2026-02-23
    Notes scanned: 307 | Topic maps: 12 | Regular claims: 284 | Inbox items: 9

    Summary: 1 FAIL, 1 WARN, 1 PASS

    FAIL:
    - [3] Link Health: 16 genuine dangling links

    WARN:
    - [2] Orphan Detection: 33 orphan notes

    PASS:
    - [1] Schema Compliance: 284/284 claims fully compliant

    ---

    [1] Schema Compliance ............ PASS
        284 claim notes checked.
        All notes fully compliant.

    [2] Orphan Detection ............. WARN
        33 orphan notes detected.
        Recommendation: run topic map integration pass on CD8+/ARIA cluster

    [3] Link Health .................. FAIL
        61 dangling link targets found across vault.
        16 genuine missing claims.
        Recommendation: fix truncated links first then decide whether uncreated claims warrant /seed

    ---
    === END REPORT ===
""")

SAMPLE_REPORT_WITH_ROOT_CAUSES = textwrap.dedent("""\
    === HEALTH REPORT ===
    Mode: quick
    Date: 2026-02-23
    Notes scanned: 307 | Topic maps: 12 | Regular claims: 284 | Inbox items: 9

    Summary: 2 FAIL, 0 WARN, 1 PASS

    FAIL:
    - [2] Description Quality: 8 descriptions need improvement
    - [3] Link Health: 16 genuine dangling links

    PASS:
    - [1] Schema Compliance: 284/284 claims fully compliant

    ---

    [1] Schema Compliance ............ PASS
        284 claim notes checked.
        All notes fully compliant.

    [2] Description Quality .......... FAIL
        8 descriptions need improvement.
        Root causes:
        - Paraphrase drift: 5 descriptions restate the title without adding new information
        - Missing mechanism: 3 descriptions lack the specific mechanism or scope

        Recommendation: run /verify on flagged notes to improve descriptions

    [3] Link Health .................. FAIL
        61 dangling link targets found across vault.
        16 genuine missing claims.
        Root causes:
        - Truncated wiki links: 4 dangling links are shortened versions of existing claims
        - Uncreated claims: 6 links reference claims that were never extracted from their source
        - Slash-in-filename: 3 macOS splits filenames containing slash into nested directories
        - Placeholder labels: 2 links use generic labels instead of actual claim titles

        Recommendation: fix truncated links first then decide whether uncreated claims warrant /seed

    ---
    === END REPORT ===
""")

ALL_PASS_REPORT = textwrap.dedent("""\
    === HEALTH REPORT ===
    Mode: quick
    Date: 2026-02-23
    Notes scanned: 307 | Topic maps: 12

    Summary: 0 FAIL, 0 WARN, 3 PASS

    PASS:
    - [1] Schema Compliance
    - [2] Orphan Detection
    - [3] Link Health

    ---

    [1] Schema Compliance ............ PASS
        All good.

    [2] Orphan Detection ............. PASS
        No orphans.

    [3] Link Health .................. PASS
        No dangling links.

    ---
    === END REPORT ===
""")


# ---------------------------------------------------------------------------
# DaemonTask
# ---------------------------------------------------------------------------


class TestDaemonTask:
    def test_to_json(self):
        task = DaemonTask(skill="tournament", args="goal-ad", model="opus", tier=1)
        parsed = json.loads(task.to_json())
        assert parsed["skill"] == "tournament"
        assert parsed["model"] == "opus"
        assert parsed["tier"] == 1


# ---------------------------------------------------------------------------
# GoalState.cycle_state
# ---------------------------------------------------------------------------


class TestGoalStateCycle:
    def test_needs_tournament(self):
        gs = GoalState(
            goal_id="g",
            hypothesis_count=10,
            undermatched_count=3,
        )
        assert gs.cycle_state == "needs_tournament"

    def test_needs_meta_review(self):
        gs = GoalState(
            goal_id="g",
            hypothesis_count=10,
            undermatched_count=0,
            latest_tournament_mtime=500.0,
            latest_meta_review_mtime=100.0,
        )
        assert gs.cycle_state == "needs_meta_review"

    def test_needs_landscape(self):
        gs = GoalState(
            goal_id="g",
            hypothesis_count=10,
            undermatched_count=0,
            latest_tournament_mtime=100.0,
            latest_meta_review_mtime=500.0,
            latest_landscape_mtime=100.0,
        )
        assert gs.cycle_state == "needs_landscape"

    def test_cycle_complete_with_new_hypotheses(self):
        gs = GoalState(
            goal_id="g",
            hypothesis_count=10,
            undermatched_count=0,
            latest_tournament_mtime=100.0,
            latest_meta_review_mtime=200.0,
            latest_landscape_mtime=300.0,
            latest_hypothesis_mtime=400.0,
        )
        assert gs.cycle_state == "cycle_complete"

    def test_cycle_stale_no_new_hypotheses(self):
        gs = GoalState(
            goal_id="g",
            hypothesis_count=10,
            undermatched_count=0,
            latest_tournament_mtime=100.0,
            latest_meta_review_mtime=200.0,
            latest_landscape_mtime=300.0,
            latest_hypothesis_mtime=50.0,
        )
        assert gs.cycle_state == "cycle_stale"

    def test_cycle_stale_when_hypothesis_equals_landscape(self):
        gs = GoalState(
            goal_id="g",
            hypothesis_count=10,
            undermatched_count=0,
            latest_tournament_mtime=100.0,
            latest_meta_review_mtime=200.0,
            latest_landscape_mtime=300.0,
            latest_hypothesis_mtime=300.0,
        )
        assert gs.cycle_state == "cycle_stale"

    def test_cycle_complete_backward_compat_zero_mtime(self):
        """All zeros with no undermatched is cycle_stale (not cycle_complete)."""
        gs = GoalState(goal_id="g", hypothesis_count=5, undermatched_count=0)
        assert gs.cycle_state == "cycle_stale"

    def test_all_zeros_is_needs_tournament_if_undermatched(self):
        gs = GoalState(goal_id="g", hypothesis_count=5, undermatched_count=5)
        assert gs.cycle_state == "needs_tournament"


# ---------------------------------------------------------------------------
# Health report parsing
# ---------------------------------------------------------------------------


class TestHealthReportParsing:
    def test_parse_summary_line(self, tmp_path):
        p = tmp_path / "report.md"
        p.write_text(SAMPLE_HEALTH_REPORT)
        hr = parse_health_report(p, max_age_hours=9999)
        assert hr.fails == 1
        assert hr.warns == 1
        assert hr.passes == 1

    def test_parse_failed_categories(self, tmp_path):
        p = tmp_path / "report.md"
        p.write_text(SAMPLE_HEALTH_REPORT)
        hr = parse_health_report(p, max_age_hours=9999)
        assert len(hr.failed_categories) == 1
        assert hr.failed_categories[0].name == "Link Health"
        assert "truncated links" in hr.failed_categories[0].recommendation

    def test_parse_all_pass(self, tmp_path):
        p = tmp_path / "report.md"
        p.write_text(ALL_PASS_REPORT)
        hr = parse_health_report(p, max_age_hours=9999)
        assert hr.fails == 0
        assert hr.warns == 0
        assert hr.passes == 3
        assert len(hr.failed_categories) == 0

    def test_missing_report(self, tmp_path):
        result = get_latest_health_report(tmp_path)
        assert result is None

    def test_stale_report(self, tmp_path):
        p = tmp_path / "report.md"
        p.write_text(SAMPLE_HEALTH_REPORT)
        hr = parse_health_report(p, max_age_hours=0)
        assert hr.stale is True

    def test_fresh_report(self, tmp_path):
        p = tmp_path / "report.md"
        p.write_text(SAMPLE_HEALTH_REPORT)
        hr = parse_health_report(p, max_age_hours=9999)
        assert hr.stale is False

    def test_get_latest_health_report(self, tmp_path):
        health_dir = tmp_path / "ops" / "health"
        health_dir.mkdir(parents=True)
        old = health_dir / "2026-02-22-report.md"
        old.write_text("old")
        import time as _time

        _time.sleep(0.05)
        new = health_dir / "2026-02-23-report.md"
        new.write_text("new")
        result = get_latest_health_report(tmp_path)
        assert result == new

    def test_nonexistent_file(self, tmp_path):
        p = tmp_path / "nope.md"
        hr = parse_health_report(p)
        assert hr.stale is True


# ---------------------------------------------------------------------------
# Health fix mapping
# ---------------------------------------------------------------------------


class TestHealthFixMapping:
    def test_schema_maps_to_validate(self, default_config):
        cat = FailedCategory(name="Schema Compliance", recommendation="fix schemas")
        task = build_health_fix_task(cat, default_config)
        assert task is not None
        assert task.skill == "validate"
        assert task.model == "haiku"

    def test_orphan_maps_to_reflect(self, default_config):
        cat = FailedCategory(name="Orphan Detection", recommendation="connect orphans")
        task = build_health_fix_task(cat, default_config)
        assert task is not None
        assert task.skill == "reflect"
        assert "--connect-orphans" in task.args

    def test_link_health_maps_to_validate(self, default_config):
        cat = FailedCategory(name="Link Health", recommendation="fix links")
        task = build_health_fix_task(cat, default_config)
        assert task is not None
        assert task.skill == "validate"
        assert "--fix-dangling" in task.args

    def test_description_quality_maps_to_verify(self, default_config):
        cat = FailedCategory(name="Description Quality", recommendation="fix descs")
        task = build_health_fix_task(cat, default_config)
        assert task is not None
        assert task.skill == "verify"

    def test_stale_notes_maps_to_reweave(self, default_config):
        cat = FailedCategory(name="Stale Notes", recommendation="reweave")
        task = build_health_fix_task(cat, default_config)
        assert task is not None
        assert task.skill == "reweave"

    def test_moc_coherence_maps_to_reflect(self, default_config):
        cat = FailedCategory(name="MOC Coherence", recommendation="update MOCs")
        task = build_health_fix_task(cat, default_config)
        assert task is not None
        assert task.skill == "reflect"

    def test_three_space_returns_none(self, default_config):
        cat = FailedCategory(name="Three-Space Boundaries", recommendation="manual fix")
        task = build_health_fix_task(cat, default_config)
        assert task is None

    def test_unknown_category_returns_none(self, default_config):
        cat = FailedCategory(name="Unknown Category")
        task = build_health_fix_task(cat, default_config)
        assert task is None

    def test_fix_task_has_tier_0(self, default_config):
        cat = FailedCategory(name="Link Health", recommendation="fix")
        task = build_health_fix_task(cat, default_config)
        assert task.tier == 0


# ---------------------------------------------------------------------------
# Priority cascade -- P1
# ---------------------------------------------------------------------------


class TestP1:
    def test_tournament_for_undermatched(
        self, vault_needing_tournament, default_config
    ):
        task = _check_p1(vault_needing_tournament, default_config)
        assert task is not None
        assert task.skill == "tournament"
        assert "goal-ad-biomarkers" in task.args

    def test_tournament_primary_goal_gets_opus(
        self, vault_needing_tournament, default_config
    ):
        task = _check_p1(vault_needing_tournament, default_config)
        assert task.model == "opus"

    def test_tournament_secondary_goal_gets_sonnet(self, default_config):
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="dynamic-biomarker-networks-ad",
                    hypothesis_count=9,
                    undermatched_count=3,
                ),
            ],
        )
        task = _check_p1(state, default_config)
        assert task.model == "sonnet"

    def test_meta_review_after_tournament(
        self, vault_needing_meta_review, default_config
    ):
        task = _check_p1(vault_needing_meta_review, default_config)
        assert task.skill == "meta-review"

    def test_landscape_after_meta_review(self, vault_needing_landscape, default_config):
        task = _check_p1(vault_needing_landscape, default_config)
        assert task.skill == "landscape"

    def test_cycle_stale_returns_none(self, idle_state, default_config):
        """cycle_stale (and cycle_complete) both return None from P1."""
        assert _check_p1(idle_state, default_config) is None

    def test_cycle_complete_returns_none(self, default_config):
        """cycle_complete also returns None from P1 (generative is Tier 3)."""
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_landscape_mtime=300.0,
                    latest_hypothesis_mtime=400.0,
                ),
            ],
        )
        assert _check_p1(state, default_config) is None

    def test_goal_priority_order(self, default_config):
        """First goal in priority order gets served first."""
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=2,
                ),
                GoalState(
                    goal_id="dynamic-biomarker-networks-ad",
                    hypothesis_count=9,
                    undermatched_count=4,
                ),
            ],
        )
        task = _check_p1(state, default_config)
        assert "goal-ad-biomarkers" in task.args

    def test_skip_goal_with_few_hypotheses(self, default_config):
        state = VaultState(
            goals=[
                GoalState(goal_id="g", hypothesis_count=1, undermatched_count=1),
            ],
        )
        assert _check_p1(state, default_config) is None


# ---------------------------------------------------------------------------
# Priority cascade -- P2
# ---------------------------------------------------------------------------


class TestP2:
    def test_observations_trigger_rethink(self, default_config):
        state = VaultState(observation_count=12)
        task = _check_p2(state, default_config)
        assert task is not None
        assert task.skill == "rethink"

    def test_tensions_trigger_rethink(self, default_config):
        state = VaultState(tension_count=7)
        task = _check_p2(state, default_config)
        assert task.skill == "rethink"

    def test_observations_before_tensions(self, default_config):
        state = VaultState(observation_count=15, tension_count=8)
        task = _check_p2(state, default_config)
        assert "observation" in task.task_key

    def test_queue_backlog_triggers_reflect(self, default_config):
        state = VaultState(queue_backlog=15)
        task = _check_p2(state, default_config)
        assert task.skill == "reflect"

    def test_below_threshold_returns_none(self, default_config):
        state = VaultState(observation_count=3, tension_count=2, queue_backlog=5)
        assert _check_p2(state, default_config) is None

    def test_orphans_trigger_reflect(self, default_config):
        state = VaultState(orphan_count=15)
        task = _check_p2(state, default_config)
        assert task is not None
        assert task.skill == "reflect"
        assert "--connect-orphans" in task.args
        assert task.task_key == "p2-reflect-orphans"

    def test_orphans_below_threshold_no_task(self, default_config):
        state = VaultState(orphan_count=5)
        assert _check_p2(state, default_config) is None

    def test_orphans_at_threshold_triggers(self, default_config):
        state = VaultState(orphan_count=10)
        task = _check_p2(state, default_config)
        assert task is not None
        assert task.skill == "reflect"

    def test_orphans_after_queue_backlog(self, default_config):
        """Queue backlog has priority over orphans in P2."""
        state = VaultState(queue_backlog=15, orphan_count=20)
        task = _check_p2(state, default_config)
        assert task.task_key == "p2-reflect-backlog"


# ---------------------------------------------------------------------------
# Orphan counting
# ---------------------------------------------------------------------------


class TestOrphanCounting:
    def test_no_notes_dir(self, tmp_path):
        assert _count_orphan_notes(tmp_path) == 0

    def test_no_orphans(self, tmp_path):
        """All notes are linked from at least one file."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        notes_dir.joinpath("claim-a.md").write_text("---\ndescription: a\n---\nBody")
        notes_dir.joinpath("claim-b.md").write_text(
            "---\ndescription: b\n---\nSee [[claim-a]]"
        )
        # A topic map links to claim-b
        topic = tmp_path / "topic.md"
        topic.write_text("# Topic\n- [[claim-b]] -- context")
        assert _count_orphan_notes(tmp_path) == 0

    def test_counts_orphans(self, tmp_path):
        """Notes with no incoming links are counted."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        notes_dir.joinpath("linked.md").write_text("---\ndescription: x\n---\nBody")
        notes_dir.joinpath("orphan-one.md").write_text("---\ndescription: y\n---\nBody")
        notes_dir.joinpath("orphan-two.md").write_text("---\ndescription: z\n---\nBody")
        # Only link to "linked"
        topic = tmp_path / "topic.md"
        topic.write_text("# Topic\n- [[linked]] -- has a link")
        assert _count_orphan_notes(tmp_path) == 2

    def test_skips_index_files(self, tmp_path):
        """_index.md is not counted as a candidate note."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        notes_dir.joinpath("_index.md").write_text("# Index")
        notes_dir.joinpath("real-note.md").write_text("---\ndescription: x\n---\n")
        # Link to real-note
        (tmp_path / "linker.md").write_text("[[real-note]]")
        assert _count_orphan_notes(tmp_path) == 0

    def test_skips_git_dir(self, tmp_path):
        """Files inside .git/ are not scanned for links."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        notes_dir.joinpath("orphan.md").write_text("---\ndescription: x\n---\n")
        # Put a link inside .git -- should be ignored
        git_dir = tmp_path / ".git" / "refs"
        git_dir.mkdir(parents=True)
        git_dir.joinpath("fake.md").write_text("[[orphan]]")
        assert _count_orphan_notes(tmp_path) == 1

    def test_empty_notes_dir(self, tmp_path):
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        assert _count_orphan_notes(tmp_path) == 0

    def test_aliased_links_count(self, tmp_path):
        """[[target|display text]] links count as links to target."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        notes_dir.joinpath("my-claim.md").write_text("---\ndescription: x\n---\n")
        (tmp_path / "linker.md").write_text("See [[my-claim|alias text]]")
        assert _count_orphan_notes(tmp_path) == 0


# ---------------------------------------------------------------------------
# Priority cascade -- P2.5
# ---------------------------------------------------------------------------


class TestP2_5:
    def test_inbox_triggers_reduce(self, default_config):
        state = VaultState(inbox_count=3)
        task = _check_p2_5(state, default_config)
        assert task is not None
        assert task.skill == "reduce"
        assert "quarantine" in task.prompt

    def test_empty_inbox_returns_none(self, default_config):
        state = VaultState(inbox_count=0)
        assert _check_p2_5(state, default_config) is None


# ---------------------------------------------------------------------------
# Priority cascade -- P3
# ---------------------------------------------------------------------------


class TestP3:
    def test_unmined_sessions_trigger_remember(self, default_config):
        state = VaultState(unmined_session_count=10)
        task = _check_p3(state, default_config)
        assert task is not None
        assert task.skill == "remember"
        assert task.batch_size == 30

    def test_stale_notes_trigger_reweave(self, default_config):
        state = VaultState(stale_note_count=5)
        task = _check_p3(state, default_config)
        assert task.skill == "reweave"

    def test_below_threshold_returns_none(self, default_config):
        state = VaultState(unmined_session_count=1)
        assert _check_p3(state, default_config) is None


# ---------------------------------------------------------------------------
# Priority cascade -- P3.5 (Federation)
# ---------------------------------------------------------------------------


class TestP3_5:
    def test_federation_enabled_with_exchange_dir(self, default_config):
        state = VaultState(
            federation_enabled=True,
            federation_exchange_dir="/tmp/exchange",
        )
        task = _check_p3_5(state, default_config)
        assert task is not None
        assert task.skill == "federation-sync"
        assert task.tier == 3
        assert task.task_key == "p3.5-federation-sync"

    def test_federation_disabled_returns_none(self, default_config):
        state = VaultState(
            federation_enabled=False,
            federation_exchange_dir="/tmp/exchange",
        )
        assert _check_p3_5(state, default_config) is None

    def test_empty_exchange_dir_returns_none(self, default_config):
        state = VaultState(
            federation_enabled=True,
            federation_exchange_dir="",
        )
        assert _check_p3_5(state, default_config) is None

    def test_both_disabled_returns_none(self, default_config):
        state = VaultState(
            federation_enabled=False,
            federation_exchange_dir="",
        )
        assert _check_p3_5(state, default_config) is None

    def test_prompt_mentions_federation(self, default_config):
        state = VaultState(
            federation_enabled=True,
            federation_exchange_dir="/tmp/exchange",
        )
        task = _check_p3_5(state, default_config)
        assert "federation" in task.prompt.lower()
        assert "ops/federation.yaml" in task.prompt


# ---------------------------------------------------------------------------
# Full cascade -- select_task (P1 is now first in cascade)
# ---------------------------------------------------------------------------


class TestSelectTask:
    def test_p1_is_first_priority(self, default_config):
        """P1 fires when there is research cycle work to do."""
        state = VaultState(
            observation_count=20,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                ),
            ],
        )
        task = select_task(state, default_config)
        assert task.tier == 1

    def test_p2_fires_when_p1_clean(self, default_config):
        """P2 fires when P1 is clean."""
        state = VaultState(
            observation_count=15,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_tournament_mtime=100.0,
                    latest_meta_review_mtime=200.0,
                    latest_landscape_mtime=300.0,
                ),
            ],
        )
        task = select_task(state, default_config)
        assert task.tier == 2
        assert task.skill == "rethink"

    def test_idle_returns_none(self, idle_state, default_config):
        assert select_task(idle_state, default_config) is None

    def test_completed_marker_skips_task(self, default_config):
        """Tasks with completed markers are skipped."""
        state = VaultState(
            observation_count=15,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_tournament_mtime=100.0,
                    latest_meta_review_mtime=200.0,
                    latest_landscape_mtime=300.0,
                ),
            ],
            completed_markers={"p2-rethink-observations"},
        )
        # P2 rethink is skipped, falls through to idle
        task = select_task(state, default_config)
        assert task is None

    def test_completed_marker_falls_through_to_next(self, default_config):
        """When P1 task is marked done, scheduler falls through to P2."""
        state = VaultState(
            observation_count=15,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                ),
            ],
            completed_markers={"p1-tournament-goal-ad-biomarkers"},
        )
        task = select_task(state, default_config)
        assert task.tier == 2
        assert task.skill == "rethink"

    def test_orphans_in_cascade(self, default_config):
        """Orphans fire at P2 level when P1 is clean and other P2 below threshold."""
        state = VaultState(
            orphan_count=15,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_tournament_mtime=100.0,
                    latest_meta_review_mtime=200.0,
                    latest_landscape_mtime=300.0,
                ),
            ],
        )
        task = select_task(state, default_config)
        assert task.tier == 2
        assert task.skill == "reflect"
        assert "--connect-orphans" in task.args

    def test_federation_fires_after_p3(self, default_config):
        """P3.5 federation fires when P1-P3 are clean."""
        state = VaultState(
            federation_enabled=True,
            federation_exchange_dir="/tmp/exchange",
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_tournament_mtime=100.0,
                    latest_meta_review_mtime=200.0,
                    latest_landscape_mtime=300.0,
                ),
            ],
        )
        task = select_task(state, default_config)
        assert task is not None
        assert task.skill == "federation-sync"

    def test_federation_skipped_when_marker_done(self, default_config):
        """Federation task is skipped when its marker exists."""
        state = VaultState(
            federation_enabled=True,
            federation_exchange_dir="/tmp/exchange",
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_tournament_mtime=100.0,
                    latest_meta_review_mtime=200.0,
                    latest_landscape_mtime=300.0,
                ),
            ],
            completed_markers={"p3.5-federation-sync"},
        )
        task = select_task(state, default_config)
        assert task is None

    def test_all_markers_done_returns_idle(self, default_config):
        """When all candidate tasks are marked done, returns None (idle)."""
        state = VaultState(
            observation_count=15,
            unmined_session_count=10,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                ),
            ],
            completed_markers={
                "p1-tournament-goal-ad-biomarkers",
                "p2-rethink-observations",
                "p3-mine-sessions",
            },
        )
        task = select_task(state, default_config)
        assert task is None

    def test_metabolic_governor_suppresses_p1(self, default_config):
        """QPR alarm suppresses generative P1, falls through to P2."""
        state = VaultState(
            observation_count=15,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                ),
            ],
            metabolic=MetabolicState(
                qpr=5.0,
                cmr=2.0,
                hcr=50.0,
                swr=1.0,
                alarm_keys=["qpr_critical"],
            ),
        )
        task = select_task(state, default_config)
        # Should skip tournament (P1 generative) and go to P2 rethink
        assert task.tier == 2
        assert task.skill == "rethink"

    def test_metabolic_governor_allows_experiment_resolution(self, default_config):
        """Even under metabolic alarm, experiment resolution still fires."""
        state = VaultState(
            observation_count=15,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                    unresolved_experiment_count=1,
                ),
            ],
            metabolic=MetabolicState(
                qpr=5.0,
                cmr=15.0,
                hcr=10.0,
                swr=1.0,
                alarm_keys=["qpr_critical", "cmr_hot"],
            ),
        )
        task = select_task(state, default_config)
        assert task.tier == 1
        assert task.skill == "experiment"
        assert "resolve" in task.args

    def test_metabolic_governor_cmr_hot_suppresses_p1(self, default_config):
        """CMR alarm also suppresses generative P1."""
        state = VaultState(
            observation_count=15,
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                ),
            ],
            metabolic=MetabolicState(
                qpr=1.0,
                cmr=15.0,
                hcr=50.0,
                swr=1.0,
                alarm_keys=["cmr_hot"],
            ),
        )
        task = select_task(state, default_config)
        assert task.tier == 2

    def test_metabolic_governor_disabled(self):
        """When metabolic is disabled, P1 fires normally."""
        config = DaemonConfig(
            goals_priority=["goal-ad-biomarkers"],
            metabolic=MetabolicConfig(enabled=False),
        )
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                ),
            ],
            metabolic=MetabolicState(qpr=5.0, alarm_keys=["qpr_critical"]),
        )
        task = select_task(state, config)
        assert task.tier == 1
        assert task.skill == "tournament"

    def test_metabolic_none_no_effect(self, default_config):
        """When metabolic is None (not computed), P1 cascade is normal."""
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                ),
            ],
            metabolic=None,
        )
        task = select_task(state, default_config)
        assert task.tier == 1


# ---------------------------------------------------------------------------
# P1 experiments only (metabolic governor helper)
# ---------------------------------------------------------------------------


class TestP1ExperimentsOnly:
    def test_returns_experiment_task(self, default_config):
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    unresolved_experiment_count=2,
                ),
            ],
        )
        task = _check_p1_experiments_only(state, default_config)
        assert task is not None
        assert task.skill == "experiment"

    def test_returns_none_no_experiments(self, default_config):
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=5,
                ),
            ],
        )
        task = _check_p1_experiments_only(state, default_config)
        assert task is None


# ---------------------------------------------------------------------------
# Inbox entries (Tier 3 human queue)
# ---------------------------------------------------------------------------


class TestInboxEntries:
    def test_cycle_complete_generates_entries(self, default_config):
        """cycle_complete (new hypotheses) generates entries."""
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_tournament_mtime=100.0,
                    latest_meta_review_mtime=200.0,
                    latest_landscape_mtime=300.0,
                    latest_hypothesis_mtime=400.0,
                ),
            ],
        )
        entries = build_inbox_entries(state, default_config)
        assert len(entries) == 2
        assert "/generate" in entries[0]
        assert "/evolve" in entries[1]

    def test_cycle_stale_no_generative_entries(self, idle_state, default_config):
        """cycle_stale (no new hypotheses) generates no generative entries."""
        entries = build_inbox_entries(idle_state, default_config)
        assert all("/generate" not in e for e in entries)
        assert all("/evolve" not in e for e in entries)

    def test_incomplete_cycle_no_entries(
        self, vault_needing_tournament, default_config
    ):
        entries = build_inbox_entries(vault_needing_tournament, default_config)
        assert len(entries) == 0


# ---------------------------------------------------------------------------
# Task stack parsing
# ---------------------------------------------------------------------------


class TestParseTaskStack:
    def test_empty_vault(self, tmp_path):
        """No tasks.md returns empty lists."""
        result = parse_task_stack(tmp_path)
        assert result["active"] == []
        assert result["pending"] == []
        assert result["completed"] == []

    def test_populated_tasks(self, tmp_path):
        """Parses active, pending, and completed sections."""
        tasks_dir = tmp_path / "ops"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.md").write_text(textwrap.dedent("""\
            # Tasks

            ## Active

            - **Submit LONI access request** -- gates all ADNI analyses
            - **Pre-register EXP-001** -- OSF registration

            ## Pending

            ### LPS Execution (Wave 1)

            - Verify FCG RNA-seq counts
            - Execute EXP-002 Steps 1-4

            ### ADNI Execution (Wave 1)

            - Download ADNI data -- after LONI approval

            ## Completed

            (none yet)
        """))
        result = parse_task_stack(tmp_path)
        assert len(result["active"]) == 2
        assert result["active"][0].title == "Submit LONI access request"
        assert result["active"][0].description == "gates all ADNI analyses"
        assert result["active"][0].section == "Active"
        assert len(result["pending"]) == 3
        assert result["pending"][0].subsection == "LPS Execution (Wave 1)"
        assert result["pending"][2].subsection == "ADNI Execution (Wave 1)"
        assert result["completed"] == []

    def test_malformed_file(self, tmp_path):
        """Non-markdown content returns empty lists gracefully."""
        tasks_dir = tmp_path / "ops"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.md").write_text("not markdown at all\n")
        result = parse_task_stack(tmp_path)
        assert result["active"] == []

    def test_items_without_bold(self, tmp_path):
        """Items without **bold** titles are parsed from plain dashes."""
        tasks_dir = tmp_path / "ops"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.md").write_text(textwrap.dedent("""\
            # Tasks

            ## Active

            - Simple task without bold -- has description
            - Another plain task
        """))
        result = parse_task_stack(tmp_path)
        assert len(result["active"]) == 2
        assert result["active"][0].title == "Simple task without bold"
        assert result["active"][0].description == "has description"
        assert result["active"][1].title == "Another plain task"
        assert result["active"][1].description == ""

    def test_unrecognized_section_ignored(self, tmp_path):
        """Sections that are not Active/Pending/Completed are ignored."""
        tasks_dir = tmp_path / "ops"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.md").write_text(textwrap.dedent("""\
            # Tasks

            ## Notes

            - This should be ignored

            ## Active

            - Real task
        """))
        result = parse_task_stack(tmp_path)
        assert len(result["active"]) == 1
        assert result["active"][0].title == "Real task"


# ---------------------------------------------------------------------------
# Tier 3 entries (task-stack-aware)
# ---------------------------------------------------------------------------


class TestBuildTier3Entries:
    def test_task_stack_items_first(self, default_config):
        """Task stack items appear before generative work."""
        state = VaultState(
            task_stack_active=[
                TaskStackItem(title="Submit LONI", section="Active"),
            ],
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_landscape_mtime=300.0,
                    latest_hypothesis_mtime=400.0,
                ),
            ],
        )
        entries = build_tier3_entries(state, default_config)
        assert entries[0] == "- [ ] Submit LONI -- from task stack"
        assert "/generate" in entries[1]

    def test_cycle_stale_filtered(self, default_config):
        """cycle_stale goals produce no generative entries."""
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_landscape_mtime=300.0,
                    latest_hypothesis_mtime=50.0,
                ),
            ],
        )
        entries = build_tier3_entries(state, default_config)
        assert all("/generate" not in e for e in entries)
        assert all("/evolve" not in e for e in entries)

    def test_empty_state(self, default_config):
        """Empty state returns empty list."""
        state = VaultState()
        entries = build_tier3_entries(state, default_config)
        assert entries == []

    def test_backward_compat_wrapper(self, default_config):
        """build_inbox_entries delegates to build_tier3_entries."""
        state = VaultState(
            task_stack_active=[
                TaskStackItem(title="Test task", section="Active"),
            ],
        )
        entries = build_inbox_entries(state, default_config)
        assert entries[0] == "- [ ] Test task -- from task stack"

    def test_metabolic_dashboard_with_alarms(self, default_config):
        """Metabolic dashboard appears as first entry when alarms active."""
        state = VaultState(
            metabolic=MetabolicState(
                qpr=5.0,
                vdr=95.0,
                cmr=19.0,
                hcr=10.0,
                swr=1.5,
                alarm_keys=["qpr_critical", "cmr_hot"],
            ),
        )
        entries = build_tier3_entries(state, default_config)
        assert len(entries) == 1
        assert "Metabolic:" in entries[0]
        assert "QPR=5.0d" in entries[0]
        assert "ALARM: qpr_critical, cmr_hot" in entries[0]

    def test_metabolic_dashboard_no_alarms(self, default_config):
        """Metabolic dashboard still appears with no alarms."""
        state = VaultState(
            metabolic=MetabolicState(
                qpr=1.0,
                vdr=50.0,
                cmr=2.0,
                hcr=50.0,
                swr=1.0,
                alarm_keys=[],
            ),
        )
        entries = build_tier3_entries(state, default_config)
        assert len(entries) == 1
        assert "ALARM: none" in entries[0]

    def test_metabolic_none_no_dashboard(self, default_config):
        """No dashboard line when metabolic is None."""
        state = VaultState(metabolic=None)
        entries = build_tier3_entries(state, default_config)
        assert entries == []

    def test_mixed_goals_cycle_states(self, default_config):
        """Only cycle_complete goals get generative entries."""
        state = VaultState(
            goals=[
                GoalState(
                    goal_id="goal-ad-biomarkers",
                    hypothesis_count=12,
                    undermatched_count=0,
                    latest_landscape_mtime=300.0,
                    latest_hypothesis_mtime=50.0,  # stale
                ),
                GoalState(
                    goal_id="lps-neuroinflammation-fcg",
                    hypothesis_count=7,
                    undermatched_count=0,
                    latest_landscape_mtime=300.0,
                    latest_hypothesis_mtime=400.0,  # complete
                ),
            ],
        )
        entries = build_tier3_entries(state, default_config)
        # Only LPS goal gets entries
        assert any("lps-neuroinflammation-fcg" in e for e in entries)
        assert not any("goal-ad-biomarkers" in e for e in entries)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestGoalSlug:
    def test_strips_prefix(self):
        assert _goal_slug("goal-ad-biomarkers") == "ad-biomarkers"

    def test_no_prefix(self):
        assert (
            _goal_slug("dynamic-biomarker-networks-ad")
            == "dynamic-biomarker-networks-ad"
        )


class TestReadFrontmatter:
    def test_valid_frontmatter(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("---\ntype: hypothesis\nid: H-001\nmatches: 5\n---\nBody text\n")
        fm = _read_frontmatter(p)
        assert fm["type"] == "hypothesis"
        assert fm["id"] == "H-001"

    def test_missing_frontmatter(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("No frontmatter here\n")
        assert _read_frontmatter(p) == {}

    def test_invalid_yaml(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("---\n: : invalid\n---\n")
        assert _read_frontmatter(p) == {}

    def test_nonexistent_file(self, tmp_path):
        p = tmp_path / "nope.md"
        assert _read_frontmatter(p) == {}


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestConfigLoading:
    def test_load_default_config(self, tmp_path):
        p = tmp_path / "daemon-config.yaml"
        p.write_text(
            yaml.dump(
                {
                    "goals_priority": ["goal-test"],
                    "models": {"tournament_primary": "opus"},
                    "cooldowns_minutes": {"after_opus": 15},
                    "batching": {"matches_per_session": 4},
                    "thresholds": {"undermatched_matches": 5},
                }
            )
        )
        cfg = load_config(p)
        assert cfg.goals_priority == ["goal-test"]
        assert cfg.models.tournament_primary == "opus"
        assert cfg.cooldowns.after_opus == 15
        assert cfg.batching.matches_per_session == 4
        assert cfg.thresholds.undermatched_matches == 5

    def test_missing_sections_use_defaults(self, tmp_path):
        p = tmp_path / "daemon-config.yaml"
        p.write_text("goals_priority:\n  - goal-x\n")
        cfg = load_config(p)
        assert cfg.models.tournament_primary == "opus"
        assert cfg.cooldowns.after_haiku == 2

    def test_empty_file(self, tmp_path):
        p = tmp_path / "daemon-config.yaml"
        p.write_text("")
        cfg = load_config(p)
        assert len(cfg.goals_priority) == 0  # defaults to empty

    def test_primary_goal(self, tmp_path):
        p = tmp_path / "daemon-config.yaml"
        p.write_text("goals_priority:\n  - my-goal\n  - other-goal\n")
        cfg = load_config(p)
        assert cfg.primary_goal == "my-goal"

    def test_cooldown_for_model(self):
        cd = DaemonConfig().cooldowns
        assert cd.for_model("haiku") == 2
        assert cd.for_model("sonnet") == 5
        assert cd.for_model("opus") == 10
        assert cd.for_model("unknown") == 5  # fallback to sonnet

    def test_model_for_tournament_primary(self):
        cfg = DaemonConfig()
        assert (
            cfg.models.for_tournament("goal-ad-biomarkers", "goal-ad-biomarkers")
            == "opus"
        )
        assert cfg.models.for_tournament("other-goal", "goal-ad-biomarkers") == "sonnet"

    def test_health_config_defaults(self):
        cfg = DaemonConfig()
        assert cfg.health.check_frequency_hours == 2
        assert cfg.health.max_fix_iterations == 3
        assert cfg.health.model == "sonnet"

    def test_health_config_from_yaml(self, tmp_path):
        p = tmp_path / "daemon-config.yaml"
        p.write_text(
            yaml.dump(
                {
                    "health": {
                        "check_frequency_hours": 4,
                        "max_fix_iterations": 5,
                        "model": "haiku",
                    },
                }
            )
        )
        cfg = load_config(p)
        assert cfg.health.check_frequency_hours == 4
        assert cfg.health.max_fix_iterations == 5
        assert cfg.health.model == "haiku"

    def test_metabolic_config_defaults(self):
        cfg = DaemonConfig()
        assert cfg.metabolic.enabled is True
        assert cfg.metabolic.qpr_critical == 3.0
        assert cfg.metabolic.cmr_hot == 10.0
        assert cfg.metabolic.hcr_redirect == 15.0
        assert cfg.metabolic.swr_archive == 5.0
        assert cfg.metabolic.vdr_warn == 80.0
        assert cfg.metabolic.lookback_days == 7

    def test_metabolic_config_from_yaml(self, tmp_path):
        p = tmp_path / "daemon-config.yaml"
        p.write_text(
            yaml.dump(
                {
                    "metabolic": {
                        "enabled": False,
                        "qpr_critical": 5.0,
                        "cmr_hot": 20.0,
                        "lookback_days": 14,
                    },
                }
            )
        )
        cfg = load_config(p)
        assert cfg.metabolic.enabled is False
        assert cfg.metabolic.qpr_critical == 5.0
        assert cfg.metabolic.cmr_hot == 20.0
        assert cfg.metabolic.lookback_days == 14
        # Unspecified fields keep defaults
        assert cfg.metabolic.hcr_redirect == 15.0


# ---------------------------------------------------------------------------
# Root cause extraction
# ---------------------------------------------------------------------------


class TestExtractRootCauses:
    def test_extract_from_report_block(self):
        block = textwrap.dedent("""\
            [3] Link Health .................. FAIL
                61 dangling link targets found across vault.
                16 genuine missing claims.
                Root causes:
                - Truncated wiki links: 4 dangling links are shortened versions of existing claims
                - Uncreated claims: 6 links reference claims that were never extracted
                - Slash-in-filename: 3 macOS splits filenames containing slash into nested directories
                - Placeholder labels: 2 links use generic labels instead of actual claim titles

                Recommendation: fix truncated links first
        """)
        causes = _extract_root_causes(block)
        assert len(causes) == 4
        assert causes[0].pattern == "Truncated wiki links"
        assert causes[0].affected_count == 4
        assert "shortened versions" in causes[0].description
        assert causes[1].pattern == "Uncreated claims"
        assert causes[1].affected_count == 6
        assert causes[2].pattern == "Slash-in-filename"
        assert causes[2].affected_count == 3
        assert causes[3].pattern == "Placeholder labels"
        assert causes[3].affected_count == 2

    def test_no_root_causes_section(self):
        block = textwrap.dedent("""\
            [3] Link Health .................. FAIL
                16 genuine missing claims.
                Recommendation: fix links
        """)
        causes = _extract_root_causes(block)
        assert causes == []

    def test_root_cause_without_count(self):
        block = textwrap.dedent("""\
            [2] Description Quality .......... FAIL
                Root causes:
                - Paraphrase drift: descriptions restate the title
        """)
        causes = _extract_root_causes(block)
        assert len(causes) == 1
        assert causes[0].pattern == "Paraphrase drift"
        assert causes[0].affected_count == 0
        assert "restate" in causes[0].description

    def test_parse_report_populates_root_causes(self, tmp_path):
        p = tmp_path / "2026-02-23-report.md"
        p.write_text(SAMPLE_REPORT_WITH_ROOT_CAUSES)
        hr = parse_health_report(p, max_age_hours=9999)
        assert len(hr.failed_categories) == 2
        # Description Quality has 2 root causes
        desc_cat = hr.failed_categories[0]
        assert desc_cat.name == "Description Quality"
        assert len(desc_cat.root_causes) == 2
        # Link Health has 4 root causes
        link_cat = hr.failed_categories[1]
        assert link_cat.name == "Link Health"
        assert len(link_cat.root_causes) == 4


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic(self):
        assert _slugify("Link Health") == "link-health"

    def test_special_chars(self):
        assert _slugify("Slash-in-filename") == "slash-in-filename"

    def test_no_path_separators(self):
        slug = _slugify("APP/PS1 model issues")
        assert "/" not in slug
        assert "\\" not in slug

    def test_truncation(self):
        long_text = "a" * 100
        assert len(_slugify(long_text)) <= 80

    def test_collapses_spaces(self):
        assert _slugify("multiple   spaces   here") == "multiple-spaces-here"


# ---------------------------------------------------------------------------
# Observation builder
# ---------------------------------------------------------------------------


class TestBuildHealthObservation:
    def test_filename_format(self):
        rc = RootCause(
            pattern="Truncated wiki links", description="short", affected_count=4
        )
        filename, content = build_health_observation(
            "Link Health", rc, "2026-02-23", "/ops/health/report.md"
        )
        assert filename == "health-link-health-truncated-wiki-links-2026-02-23"
        assert "/" not in filename
        assert "\\" not in filename

    def test_content_schema(self):
        rc = RootCause(
            pattern="Slash-in-filename", description="macOS issue", affected_count=3
        )
        filename, content = build_health_observation(
            "Link Health", rc, "2026-02-23", "/ops/health/report.md"
        )
        assert "category: health-pattern" in content
        assert "status: pending" in content
        assert 'health_category: "Link Health"' in content
        assert 'failure_pattern: "Slash-in-filename"' in content
        assert "affected_count: 3" in content
        assert "Related: [[observations]]" not in content

    def test_content_body(self):
        rc = RootCause(
            pattern="Test pattern", description="test desc", affected_count=7
        )
        _, content = build_health_observation("Cat", rc, "2026-02-23", "/r.md")
        assert "**Pattern:** Test pattern" in content
        assert "**Description:** test desc" in content
        assert "Affected count: 7" in content

    def test_zero_count_omits_count_line(self):
        rc = RootCause(pattern="Test", description="desc", affected_count=0)
        _, content = build_health_observation("Cat", rc, "2026-02-23", "/r.md")
        assert "Affected count:" not in content


# ---------------------------------------------------------------------------
# Observation creation (filesystem)
# ---------------------------------------------------------------------------


class TestCreateHealthObservations:
    def test_creates_observations_from_report(self, tmp_path):
        """Full integration: report with root causes -> observation files."""
        # Set up vault structure
        health_dir = tmp_path / "ops" / "health"
        health_dir.mkdir(parents=True)
        obs_dir = tmp_path / "ops" / "observations"

        report = health_dir / "2026-02-23-report.md"
        report.write_text(SAMPLE_REPORT_WITH_ROOT_CAUSES)

        created = create_health_observations(tmp_path, report)
        assert len(created) == 6  # 2 from Description Quality + 4 from Link Health
        assert obs_dir.is_dir()
        for name in created:
            assert (obs_dir / f"{name}.md").is_file()

    def test_idempotent_no_duplicates(self, tmp_path):
        """Running twice on same report creates no duplicates."""
        health_dir = tmp_path / "ops" / "health"
        health_dir.mkdir(parents=True)

        report = health_dir / "2026-02-23-report.md"
        report.write_text(SAMPLE_REPORT_WITH_ROOT_CAUSES)

        first_run = create_health_observations(tmp_path, report)
        assert len(first_run) == 6

        second_run = create_health_observations(tmp_path, report)
        assert len(second_run) == 0  # all already exist

    def test_no_observations_for_clean_report(self, tmp_path):
        """0 FAIL = 0 observations."""
        health_dir = tmp_path / "ops" / "health"
        health_dir.mkdir(parents=True)

        report = health_dir / "2026-02-23-report.md"
        report.write_text(ALL_PASS_REPORT)

        created = create_health_observations(tmp_path, report)
        assert created == []

    def test_no_observations_without_report(self, tmp_path):
        """No report path and no reports in vault -> empty list."""
        created = create_health_observations(tmp_path)
        assert created == []

    def test_date_extracted_from_filename(self, tmp_path):
        """Report date comes from filename, not hardcoded."""
        health_dir = tmp_path / "ops" / "health"
        health_dir.mkdir(parents=True)

        report = health_dir / "2026-03-15-report.md"
        report.write_text(SAMPLE_REPORT_WITH_ROOT_CAUSES)

        created = create_health_observations(tmp_path, report)
        assert all("2026-03-15" in name for name in created)

    def test_uses_latest_report_when_none_specified(self, tmp_path):
        """When report_path=None, uses get_latest_health_report."""
        health_dir = tmp_path / "ops" / "health"
        health_dir.mkdir(parents=True)

        report = health_dir / "2026-02-23-report.md"
        report.write_text(SAMPLE_REPORT_WITH_ROOT_CAUSES)

        created = create_health_observations(tmp_path)
        assert len(created) == 6

    def test_observation_content_parseable(self, tmp_path):
        """Created observations have valid YAML frontmatter."""
        health_dir = tmp_path / "ops" / "health"
        health_dir.mkdir(parents=True)
        obs_dir = tmp_path / "ops" / "observations"

        report = health_dir / "2026-02-23-report.md"
        report.write_text(SAMPLE_REPORT_WITH_ROOT_CAUSES)

        create_health_observations(tmp_path, report)

        # Check one observation file has parseable frontmatter
        for md_file in obs_dir.glob("*.md"):
            from engram_r.daemon_scheduler import _read_frontmatter

            fm = _read_frontmatter(md_file)
            assert fm.get("category") == "health-pattern"
            assert fm.get("status") == "pending"
            assert "health_category" in fm
            assert "failure_pattern" in fm
            break  # just check one


# ---------------------------------------------------------------------------
# scan_vault reads completed markers
# ---------------------------------------------------------------------------


class TestScanVaultMarkers:
    def test_reads_marker_files(self, tmp_path):
        """scan_vault populates completed_markers from ops/daemon/markers/."""
        # Minimal vault structure
        (tmp_path / "ops").mkdir()
        (tmp_path / "ops" / "daemon" / "markers").mkdir(parents=True)
        (
            tmp_path / "ops" / "daemon" / "markers" / "p1-landscape-goal-ad.done"
        ).write_text("2026-02-23")
        (tmp_path / "ops" / "daemon" / "markers" / "p3-mine-sessions.done").write_text(
            "2026-02-23"
        )
        config_path = tmp_path / "ops" / "daemon-config.yaml"
        config_path.write_text("goals_priority:\n  - goal-test\n")
        config = load_config(config_path)
        state = scan_vault(tmp_path, config)
        assert "p1-landscape-goal-ad" in state.completed_markers
        assert "p3-mine-sessions" in state.completed_markers

    def test_empty_marker_dir(self, tmp_path):
        """No markers -> empty set."""
        (tmp_path / "ops" / "daemon" / "markers").mkdir(parents=True)
        config_path = tmp_path / "ops" / "daemon-config.yaml"
        config_path.write_text("goals_priority:\n  - goal-test\n")
        config = load_config(config_path)
        state = scan_vault(tmp_path, config)
        assert state.completed_markers == set()

    def test_no_marker_dir(self, tmp_path):
        """Missing marker directory -> empty set."""
        (tmp_path / "ops").mkdir(parents=True)
        config_path = tmp_path / "ops" / "daemon-config.yaml"
        config_path.write_text("goals_priority:\n  - goal-test\n")
        config = load_config(config_path)
        state = scan_vault(tmp_path, config)
        assert state.completed_markers == set()


class TestScanVaultFederation:
    """Test that scan_vault reads federation config from ops/federation.yaml."""

    def test_federation_enabled(self, tmp_path):
        (tmp_path / "ops").mkdir(parents=True)
        config_path = tmp_path / "ops" / "daemon-config.yaml"
        config_path.write_text("goals_priority: []\n")
        fed_path = tmp_path / "ops" / "federation.yaml"
        fed_path.write_text(
            yaml.dump(
                {
                    "enabled": True,
                    "sync": {"exchange_dir": "/tmp/exchange"},
                    "peers": {
                        "peer-a": {"trust": "full"},
                        "peer-b": {"trust": "verified"},
                    },
                }
            )
        )
        config = load_config(config_path)
        state = scan_vault(tmp_path, config)
        assert state.federation_enabled is True
        assert state.federation_exchange_dir == "/tmp/exchange"
        assert state.federation_peers_count == 2

    def test_federation_disabled(self, tmp_path):
        (tmp_path / "ops").mkdir(parents=True)
        config_path = tmp_path / "ops" / "daemon-config.yaml"
        config_path.write_text("goals_priority: []\n")
        fed_path = tmp_path / "ops" / "federation.yaml"
        fed_path.write_text(yaml.dump({"enabled": False}))
        config = load_config(config_path)
        state = scan_vault(tmp_path, config)
        assert state.federation_enabled is False

    def test_no_federation_config(self, tmp_path):
        (tmp_path / "ops").mkdir(parents=True)
        config_path = tmp_path / "ops" / "daemon-config.yaml"
        config_path.write_text("goals_priority: []\n")
        config = load_config(config_path)
        state = scan_vault(tmp_path, config)
        assert state.federation_enabled is False
        assert state.federation_exchange_dir == ""
        assert state.federation_peers_count == 0


class TestDefaultVaultPath:
    """Test _default_vault_path() registry-first resolution."""

    def test_registry_takes_priority(self, tmp_path, monkeypatch):
        """Registry default vault path wins over VAULT_PATH env var."""
        from unittest.mock import patch

        reg = tmp_path / "vaults.yaml"
        reg.write_text(
            yaml.dump(
                {
                    "vaults": [
                        {
                            "name": "main",
                            "path": str(tmp_path / "registry-vault"),
                            "default": True,
                        }
                    ]
                }
            )
        )
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "env-vault"))
        with patch("engram_r.vault_registry._DEFAULT_REGISTRY_PATH", reg):
            result = _default_vault_path()
        assert result == (tmp_path / "registry-vault").resolve()

    def test_env_var_fallback(self, tmp_path, monkeypatch):
        """VAULT_PATH env var used when registry is absent."""
        from unittest.mock import patch

        missing = tmp_path / "nonexistent.yaml"
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "env-vault"))
        with patch("engram_r.vault_registry._DEFAULT_REGISTRY_PATH", missing):
            result = _default_vault_path()
        assert result == tmp_path / "env-vault"

    def test_file_location_fallback(self, tmp_path, monkeypatch):
        """Falls back to walking up from __file__ when nothing else works."""
        from unittest.mock import patch

        missing = tmp_path / "nonexistent.yaml"
        monkeypatch.delenv("VAULT_PATH", raising=False)
        with patch("engram_r.vault_registry._DEFAULT_REGISTRY_PATH", missing):
            result = _default_vault_path()
        # Should be a valid path (the project root)
        assert result.is_absolute()


# ---------------------------------------------------------------------------
# _check_schedules
# ---------------------------------------------------------------------------


class TestCheckSchedules:
    """Tests for _check_schedules -- schedule evaluation in the priority cascade."""

    def test_returns_none_when_no_schedules(self):
        config = DaemonConfig(schedules=[])
        state = VaultState()
        assert _check_schedules(state, config) is None

    def test_returns_none_when_wrong_day(self, monkeypatch):
        import datetime as _dt

        # Pin "now" to a Tuesday at 10:00
        fixed = _dt.datetime(2026, 2, 24, 10, 0)
        monkeypatch.setattr(
            "engram_r.daemon_scheduler.datetime",
            type(
                "dt",
                (),
                {
                    "datetime": type(
                        "dt_inner", (), {"now": staticmethod(lambda: fixed)}
                    )
                },
            )(),
        )
        entry = ScheduleEntry(
            name="weekly-test", cadence="weekly", day="monday", hour=9, enabled=True
        )
        config = DaemonConfig(schedules=[entry])
        state = VaultState()
        assert _check_schedules(state, config) is None

    def test_returns_none_before_hour(self, monkeypatch):
        import datetime as _dt

        # Pin "now" to Monday at 07:00 (before hour=9)
        fixed = _dt.datetime(2026, 2, 23, 7, 0)
        monkeypatch.setattr(
            "engram_r.daemon_scheduler.datetime",
            type(
                "dt",
                (),
                {
                    "datetime": type(
                        "dt_inner", (), {"now": staticmethod(lambda: fixed)}
                    )
                },
            )(),
        )
        entry = ScheduleEntry(
            name="weekly-test", cadence="weekly", day="monday", hour=9, enabled=True
        )
        config = DaemonConfig(schedules=[entry])
        state = VaultState()
        assert _check_schedules(state, config) is None

    def test_returns_task_when_due(self, monkeypatch):
        import datetime as _dt

        # Pin "now" to Monday at 10:00
        fixed = _dt.datetime(2026, 2, 23, 10, 0)
        monkeypatch.setattr(
            "engram_r.daemon_scheduler.datetime",
            type(
                "dt",
                (),
                {
                    "datetime": type(
                        "dt_inner", (), {"now": staticmethod(lambda: fixed)}
                    )
                },
            )(),
        )
        entry = ScheduleEntry(
            name="weekly-test",
            type="project_update",
            cadence="weekly",
            day="monday",
            hour=9,
            enabled=True,
        )
        config = DaemonConfig(schedules=[entry])
        state = VaultState()
        task = _check_schedules(state, config)
        assert task is not None
        assert task.skill == "notify-scheduled"
        assert task.args == "weekly-test"
        assert task.task_key.startswith("sched-weekly-test-")

    def test_skips_disabled_entries(self, monkeypatch):
        import datetime as _dt

        fixed = _dt.datetime(2026, 2, 23, 10, 0)
        monkeypatch.setattr(
            "engram_r.daemon_scheduler.datetime",
            type(
                "dt",
                (),
                {
                    "datetime": type(
                        "dt_inner", (), {"now": staticmethod(lambda: fixed)}
                    )
                },
            )(),
        )
        entry = ScheduleEntry(
            name="weekly-test", cadence="weekly", day="monday", hour=9, enabled=False
        )
        config = DaemonConfig(schedules=[entry])
        state = VaultState()
        assert _check_schedules(state, config) is None

    def test_skips_completed_marker(self, monkeypatch):
        import datetime as _dt

        fixed = _dt.datetime(2026, 2, 23, 10, 0)
        monkeypatch.setattr(
            "engram_r.daemon_scheduler.datetime",
            type(
                "dt",
                (),
                {
                    "datetime": type(
                        "dt_inner", (), {"now": staticmethod(lambda: fixed)}
                    )
                },
            )(),
        )
        entry = ScheduleEntry(
            name="weekly-test", cadence="weekly", day="monday", hour=9, enabled=True
        )
        config = DaemonConfig(schedules=[entry])
        # Marker for ISO week 9, 2026
        state = VaultState(completed_markers={"sched-weekly-test-2026-W09"})
        assert _check_schedules(state, config) is None

    def test_returns_first_eligible(self, monkeypatch):
        import datetime as _dt

        fixed = _dt.datetime(2026, 2, 23, 10, 0)
        monkeypatch.setattr(
            "engram_r.daemon_scheduler.datetime",
            type(
                "dt",
                (),
                {
                    "datetime": type(
                        "dt_inner", (), {"now": staticmethod(lambda: fixed)}
                    )
                },
            )(),
        )
        entry_a = ScheduleEntry(
            name="already-done", cadence="weekly", day="monday", hour=9, enabled=True
        )
        entry_b = ScheduleEntry(
            name="not-done", cadence="weekly", day="monday", hour=9, enabled=True
        )
        config = DaemonConfig(schedules=[entry_a, entry_b])
        state = VaultState(completed_markers={"sched-already-done-2026-W09"})
        task = _check_schedules(state, config)
        assert task is not None
        assert task.args == "not-done"
