"""Tests for metabolic indicators -- daemon self-regulation metrics."""

import json
from datetime import UTC, datetime, timedelta

from engram_r.metabolic_indicators import (
    MetabolicState,
    classify_alarms,
    compute_cmr,
    compute_hcr,
    compute_metabolic_state,
    compute_qpr,
    compute_swr,
    compute_vdr,
)

# ---------------------------------------------------------------------------
# QPR (Queue Pressure Ratio)
# ---------------------------------------------------------------------------


class TestComputeQPR:
    def test_with_recent_completions(self):
        """QPR = backlog / daily_rate."""
        now = datetime.now(UTC)
        queue_data = {
            "tasks": [
                {"id": "t1", "status": "pending"},
                {"id": "t2", "status": "pending"},
                {"id": "t3", "status": "pending"},
                {
                    "id": "t4",
                    "status": "done",
                    "completed": (now - timedelta(days=1)).isoformat(),
                },
                {
                    "id": "t5",
                    "status": "done",
                    "completed": (now - timedelta(days=2)).isoformat(),
                },
                {
                    "id": "t6",
                    "status": "done",
                    "completed": (now - timedelta(days=3)).isoformat(),
                },
                {
                    "id": "t7",
                    "status": "done",
                    "completed": (now - timedelta(days=6)).isoformat(),
                },
            ]
        }
        # 3 pending, 4 completed in 7 days -> rate = 4/7 -> QPR = 3 / (4/7) = 5.25
        qpr = compute_qpr(queue_data=queue_data, lookback_days=7)
        assert abs(qpr - 5.25) < 0.01

    def test_no_completions_uses_floor_rate(self):
        """When no completions, use floor rate of 0.1."""
        queue_data = {
            "tasks": [
                {"id": "t1", "status": "pending"},
                {"id": "t2", "status": "pending"},
            ]
        }
        qpr = compute_qpr(queue_data=queue_data, lookback_days=7)
        # 2 pending / 0.1 = 20
        assert abs(qpr - 20.0) < 0.01

    def test_all_done_zero_backlog(self):
        """QPR is 0 when no pending tasks."""
        now = datetime.now(UTC)
        queue_data = {
            "tasks": [
                {
                    "id": "t1",
                    "status": "done",
                    "completed": (now - timedelta(days=1)).isoformat(),
                },
            ]
        }
        assert compute_qpr(queue_data=queue_data) == 0.0

    def test_empty_queue(self):
        assert compute_qpr(queue_data={"tasks": []}) == 0.0

    def test_none_queue_no_path(self):
        assert compute_qpr(queue_data=None, queue_path=None) == 0.0

    def test_reads_from_disk(self, tmp_path):
        """Reads queue.json from disk when queue_data is None."""
        now = datetime.now(UTC)
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(
            json.dumps(
                {
                    "tasks": [
                        {"id": "t1", "status": "pending"},
                        {
                            "id": "t2",
                            "status": "done",
                            "completed": now.isoformat(),
                        },
                    ]
                }
            )
        )
        qpr = compute_qpr(queue_path=queue_file, lookback_days=7)
        # 1 pending, 1 completed in 7d -> rate = 1/7 -> QPR = 1 / (1/7) = 7
        assert abs(qpr - 7.0) < 0.01

    def test_old_completions_excluded(self):
        """Completions outside lookback window are not counted."""
        now = datetime.now(UTC)
        queue_data = {
            "tasks": [
                {"id": "t1", "status": "pending"},
                {
                    "id": "t2",
                    "status": "done",
                    "completed": (now - timedelta(days=30)).isoformat(),
                },
            ]
        }
        # 1 pending, 0 recent completions -> floor rate 0.1 -> QPR = 10
        qpr = compute_qpr(queue_data=queue_data, lookback_days=7)
        assert abs(qpr - 10.0) < 0.01


# ---------------------------------------------------------------------------
# VDR (Verification Debt Ratio)
# ---------------------------------------------------------------------------


class TestComputeVDR:
    def test_all_agent_verified(self, tmp_path):
        """100% debt when all are agent-verified."""
        notes = tmp_path / "notes"
        notes.mkdir()
        for i in range(5):
            (notes / f"note-{i}.md").write_text(
                '---\nverified_by: "agent"\n---\nContent\n'
            )
        assert compute_vdr(notes) == 100.0

    def test_mixed_verification(self, tmp_path):
        """Partial human verification."""
        notes = tmp_path / "notes"
        notes.mkdir()
        for i in range(3):
            (notes / f"agent-{i}.md").write_text(
                '---\nverified_by: "agent"\n---\nContent\n'
            )
        for i in range(2):
            (notes / f"human-{i}.md").write_text(
                '---\nverified_by: "human"\n---\nContent\n'
            )
        # 3/5 = 60% debt
        assert abs(compute_vdr(notes) - 60.0) < 0.01

    def test_all_human_verified(self, tmp_path):
        notes = tmp_path / "notes"
        notes.mkdir()
        for i in range(3):
            (notes / f"note-{i}.md").write_text(
                '---\nverified_by: "human"\n---\nContent\n'
            )
        assert compute_vdr(notes) == 0.0

    def test_empty_dir(self, tmp_path):
        notes = tmp_path / "notes"
        notes.mkdir()
        assert compute_vdr(notes) == 0.0

    def test_missing_dir(self, tmp_path):
        assert compute_vdr(tmp_path / "nonexistent") == 0.0

    def test_skips_index(self, tmp_path):
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "_index.md").write_text("---\n---\nIndex\n")
        (notes / "note.md").write_text('---\nverified_by: "agent"\n---\n')
        assert compute_vdr(notes) == 100.0  # Only 1 note (index excluded)


# ---------------------------------------------------------------------------
# CMR (Creation:Maintenance Ratio)
# ---------------------------------------------------------------------------


class TestComputeCMR:
    def test_balanced_ratio(self, tmp_path):
        """When creation and maintenance are equal, CMR = 1."""
        notes = tmp_path / "notes"
        notes.mkdir()
        today = datetime.now(UTC).date().isoformat()
        for i in range(3):
            (notes / f"note-{i}.md").write_text(
                f'---\ncreated: "{today}"\n---\nContent\n'
            )

        now = datetime.now(UTC)
        queue_data = {
            "tasks": [
                {
                    "id": f"claim-{i}",
                    "type": "claim",
                    "status": "done",
                    "completed_phases": ["create", "reflect", "reweave"],
                    "completed": (now - timedelta(days=1)).isoformat(),
                }
                for i in range(3)
            ]
        }
        cmr = compute_cmr(notes, queue_data=queue_data, lookback_days=7)
        assert abs(cmr - 1.0) < 0.01

    def test_creation_dominant(self, tmp_path):
        """High creation, no maintenance -> ratio = creation/1."""
        notes = tmp_path / "notes"
        notes.mkdir()
        today = datetime.now(UTC).date().isoformat()
        for i in range(15):
            (notes / f"note-{i}.md").write_text(
                f'---\ncreated: "{today}"\n---\nContent\n'
            )
        cmr = compute_cmr(notes, queue_data={"tasks": []}, lookback_days=7)
        assert cmr == 15.0  # 15 / max(0,1) = 15

    def test_maintenance_only(self, tmp_path):
        """No recent creation, some maintenance -> CMR = 1/N."""
        notes = tmp_path / "notes"
        notes.mkdir()
        # Old note (created more than 7 days ago, old ctime via fallback)
        old = notes / "old-note.md"
        old.write_text('---\ncreated: "2020-01-01"\n---\nContent\n')

        now = datetime.now(UTC)
        queue_data = {
            "tasks": [
                {
                    "id": "claim-1",
                    "type": "claim",
                    "status": "done",
                    "completed_phases": ["create", "reflect"],
                    "completed": (now - timedelta(days=1)).isoformat(),
                }
            ]
        }
        cmr = compute_cmr(notes, queue_data=queue_data, lookback_days=7)
        # 0 recent creation -> max(0,1)=1, 1 maintenance -> 1/1 = 1
        assert abs(cmr - 1.0) < 0.01


# ---------------------------------------------------------------------------
# HCR (Hypothesis Conversion Rate)
# ---------------------------------------------------------------------------


class TestComputeHCR:
    def _write_hyp(self, d, name, status):
        (d / f"{name}.md").write_text(
            f'---\ntype: "hypothesis"\nstatus: "{status}"\n---\nContent\n'
        )

    def test_low_conversion(self, tmp_path):
        hyp_dir = tmp_path / "hypotheses"
        hyp_dir.mkdir()
        self._write_hyp(hyp_dir, "h1", "active")
        self._write_hyp(hyp_dir, "h2", "active")
        self._write_hyp(hyp_dir, "h3", "active")
        self._write_hyp(hyp_dir, "h4", "active")
        self._write_hyp(hyp_dir, "h5", "tested-positive")
        # 1/5 = 20%
        assert abs(compute_hcr(hyp_dir) - 20.0) < 0.01

    def test_counts_all_converted_statuses(self, tmp_path):
        hyp_dir = tmp_path / "hypotheses"
        hyp_dir.mkdir()
        self._write_hyp(hyp_dir, "h1", "tested-positive")
        self._write_hyp(hyp_dir, "h2", "tested-negative")
        self._write_hyp(hyp_dir, "h3", "executing")
        self._write_hyp(hyp_dir, "h4", "sap-written")
        self._write_hyp(hyp_dir, "h5", "active")
        # 4/5 = 80%
        assert abs(compute_hcr(hyp_dir) - 80.0) < 0.01

    def test_empty_dir(self, tmp_path):
        hyp_dir = tmp_path / "hypotheses"
        hyp_dir.mkdir()
        assert compute_hcr(hyp_dir) == 0.0

    def test_missing_dir(self, tmp_path):
        assert compute_hcr(tmp_path / "nonexistent") == 0.0

    def test_skips_non_hypothesis(self, tmp_path):
        hyp_dir = tmp_path / "hypotheses"
        hyp_dir.mkdir()
        self._write_hyp(hyp_dir, "h1", "active")
        (hyp_dir / "readme.md").write_text('---\ntype: "note"\n---\nNot a hypothesis\n')
        (hyp_dir / "_index.md").write_text("---\n---\nIndex\n")
        assert abs(compute_hcr(hyp_dir) - 0.0) < 0.01  # 0/1 = 0%


# ---------------------------------------------------------------------------
# SWR (Session Waste Ratio)
# ---------------------------------------------------------------------------


class TestComputeSWR:
    def test_normal_ratio(self, tmp_path):
        sessions = tmp_path / "sessions"
        sessions.mkdir()
        notes = tmp_path / "notes"
        notes.mkdir()
        hyps = tmp_path / "hypotheses"
        hyps.mkdir()

        for i in range(10):
            (sessions / f"session-{i}.md").write_text("# session\n")
        for i in range(5):
            (notes / f"note-{i}.md").write_text("---\n---\n")
        for i in range(5):
            (hyps / f"h-{i}.md").write_text("---\n---\n")

        # 10 sessions / 10 artifacts = 1.0
        assert abs(compute_swr(sessions, notes, hyps) - 1.0) < 0.01

    def test_high_ratio(self, tmp_path):
        sessions = tmp_path / "sessions"
        sessions.mkdir()
        notes = tmp_path / "notes"
        notes.mkdir()
        hyps = tmp_path / "hypotheses"
        hyps.mkdir()

        for i in range(20):
            (sessions / f"session-{i}.md").write_text("# session\n")
        for i in range(2):
            (notes / f"note-{i}.md").write_text("---\n---\n")

        # 20 sessions / 2 artifacts = 10.0
        assert abs(compute_swr(sessions, notes, hyps) - 10.0) < 0.01

    def test_no_sessions(self, tmp_path):
        sessions = tmp_path / "sessions"
        sessions.mkdir()
        notes = tmp_path / "notes"
        notes.mkdir()
        hyps = tmp_path / "hypotheses"
        hyps.mkdir()
        (notes / "note.md").write_text("---\n---\n")
        assert compute_swr(sessions, notes, hyps) == 0.0


# ---------------------------------------------------------------------------
# Alarm classification
# ---------------------------------------------------------------------------


class TestClassifyAlarms:
    def test_multiple_alarms(self):
        state = MetabolicState(qpr=5.0, cmr=15.0, hcr=10.0, swr=6.0)
        alarms = classify_alarms(state)
        assert "qpr_critical" in alarms
        assert "cmr_hot" in alarms
        assert "hcr_low" in alarms
        assert "swr_high" in alarms

    def test_no_alarms_healthy(self):
        state = MetabolicState(qpr=1.0, cmr=2.0, hcr=50.0, swr=1.0)
        alarms = classify_alarms(state)
        assert alarms == []

    def test_qpr_only(self):
        state = MetabolicState(qpr=4.0, cmr=2.0, hcr=50.0, swr=1.0)
        alarms = classify_alarms(state)
        assert alarms == ["qpr_critical"]

    def test_custom_thresholds(self):
        state = MetabolicState(qpr=2.0, cmr=5.0, hcr=50.0, swr=1.0)
        # Default thresholds: no alarms
        assert classify_alarms(state) == []
        # Lower thresholds: alarms
        alarms = classify_alarms(state, qpr_critical=1.0, cmr_hot=3.0)
        assert "qpr_critical" in alarms
        assert "cmr_hot" in alarms

    def test_vdr_not_alarmed(self):
        """VDR is informational only -- never triggers alarms."""
        state = MetabolicState(vdr=99.9, qpr=1.0, cmr=2.0, hcr=50.0, swr=1.0)
        assert classify_alarms(state) == []


# ---------------------------------------------------------------------------
# End-to-end integration
# ---------------------------------------------------------------------------


class TestComputeMetabolicState:
    def test_end_to_end(self, tmp_path):
        """Integration test with a temp vault."""
        # Set up vault structure
        notes = tmp_path / "notes"
        notes.mkdir()
        hyps = tmp_path / "_research" / "hypotheses"
        hyps.mkdir(parents=True)
        sessions = tmp_path / "ops" / "sessions"
        sessions.mkdir(parents=True)
        queue_dir = tmp_path / "ops" / "queue"
        queue_dir.mkdir(parents=True)

        # Create some notes
        today = datetime.now(UTC).date().isoformat()
        for i in range(5):
            (notes / f"note-{i}.md").write_text(
                f'---\nverified_by: "agent"\ncreated: "{today}"\n---\n'
            )

        # Create some hypotheses
        for i in range(4):
            (hyps / f"h-{i}.md").write_text(
                '---\ntype: "hypothesis"\nstatus: "active"\n---\n'
            )
        (hyps / "h-4.md").write_text(
            '---\ntype: "hypothesis"\nstatus: "tested-positive"\n---\n'
        )

        # Create sessions
        for i in range(3):
            (sessions / f"session-{i}.md").write_text("# session\n")

        # Create queue
        now = datetime.now(UTC)
        queue = {
            "tasks": [
                {"id": "t1", "status": "pending"},
                {"id": "t2", "status": "pending"},
                {
                    "id": "t3",
                    "type": "claim",
                    "status": "done",
                    "completed_phases": ["create", "reflect"],
                    "completed": (now - timedelta(days=1)).isoformat(),
                },
            ]
        }
        (queue_dir / "queue.json").write_text(json.dumps(queue))

        state = compute_metabolic_state(tmp_path)

        # QPR: 2 pending, 1 recent completion -> rate=1/7, QPR=2/(1/7)=14
        assert state.qpr > 0
        # VDR: 5 agent, 0 human -> 100%
        assert state.vdr == 100.0
        # HCR: 1/5 = 20%
        assert abs(state.hcr - 20.0) < 0.01
        # SWR: 3 sessions / 10 artifacts = 0.3
        assert state.swr > 0
        # Alarms should include qpr_critical (14 > 3)
        assert "qpr_critical" in state.alarm_keys
