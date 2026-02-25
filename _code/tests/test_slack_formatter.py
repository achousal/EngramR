"""Tests for engram_r.slack_formatter."""

from __future__ import annotations

from engram_r.slack_formatter import (
    _format_duration,
    format_daily_parent,
    format_daemon_alert,
    format_daemon_for_you,
    format_daemon_task_complete,
    format_inbound_summary,
    format_meta_review,
    format_session_end,
    format_session_start,
    format_tournament_result,
)


class TestFormatDuration:
    def test_seconds_only(self):
        assert _format_duration(45) == "45s"

    def test_minutes(self):
        assert _format_duration(120) == "2m"

    def test_minutes_and_seconds(self):
        assert _format_duration(125) == "2m 5s"

    def test_hours(self):
        assert _format_duration(3720) == "1h 2m"


class TestDailyParent:
    def test_returns_tuple(self):
        text, blocks = format_daily_parent("2026-02-23")
        assert "2026-02-23" in text
        assert len(blocks) == 2
        assert blocks[0]["type"] == "header"


class TestSessionStart:
    def test_minimal(self):
        text, blocks = format_session_start()
        assert "Session started" in text
        assert len(blocks) >= 1

    def test_with_goals_and_stats(self):
        text, blocks = format_session_start(
            goals=["AD biomarkers", "LPS inflammation"],
            vault_stats={"claims": 311, "inbox": 9},
            top_hypotheses=["1. H-AD-004b (Elo 1338)"],
        )
        assert "Session started" in text
        # Collect all text from blocks (sections have text.text, context has elements)
        all_text_parts = []
        for b in blocks:
            if isinstance(b.get("text"), dict):
                all_text_parts.append(b["text"].get("text", ""))
            for elem in b.get("elements", []):
                if isinstance(elem, dict):
                    all_text_parts.append(elem.get("text", ""))
        block_texts = " ".join(all_text_parts)
        assert "AD biomarkers" in block_texts
        assert "311" in block_texts


class TestSessionEnd:
    def test_minimal(self):
        text, blocks = format_session_end()
        assert "Session ended" in text

    def test_with_details(self):
        text, blocks = format_session_end(
            session_id="abc12345-xyz",
            files_written=["notes/foo.md", "notes/bar.md"],
            skills_invoked=["/generate", "/tournament"],
            summary="Generated 4 hypotheses and ran 8 matches",
            duration_s=300,
        )
        assert "abc12345" in text
        block_texts = " ".join(
            b.get("text", {}).get("text", "")
            for b in blocks
            if isinstance(b.get("text"), dict)
        )
        assert "/generate" in block_texts


class TestDaemonTaskComplete:
    def test_basic(self):
        text, blocks = format_daemon_task_complete(
            skill="tournament", task_key="tourn-ad-001", model="opus", elapsed_s=120
        )
        assert "tournament" in text
        assert len(blocks) >= 1


class TestDaemonAlert:
    def test_basic(self):
        text, blocks = format_daemon_alert("5 consecutive fast fails")
        assert "alert" in text.lower()
        assert "5 consecutive" in blocks[0]["text"]["text"]


class TestDaemonForYou:
    def test_empty(self):
        text, blocks = format_daemon_for_you()
        assert "0 item(s)" in text

    def test_with_entries(self):
        text, blocks = format_daemon_for_you(
            entries=["Review H-AD-009 draft", "Approve /rethink proposal"]
        )
        assert "2 item(s)" in text
        assert len(blocks) == 2


class TestTournamentResult:
    def test_basic(self):
        text, blocks = format_tournament_result(
            goal_id="ad-biomarkers",
            matches=8,
            top_hypotheses=["1. H-AD-004b (1338)", "2. H-AD-003b (1294)"],
        )
        assert "ad-biomarkers" in text
        block_texts = " ".join(
            b.get("text", {}).get("text", "")
            for b in blocks
            if isinstance(b.get("text"), dict)
        )
        assert "H-AD-004b" in block_texts


class TestMetaReview:
    def test_basic(self):
        text, blocks = format_meta_review(
            goal_id="ad-biomarkers",
            hypotheses_reviewed=12,
            matches_analyzed=74,
            key_patterns=["Gen-2 evolutions dominate"],
        )
        assert "12 hyps" in text
        assert "74 matches" in text


class TestInboundSummary:
    def test_empty_returns_empty(self):
        assert format_inbound_summary([]) == ""

    def test_formats_messages(self):
        msgs = [
            {"user": "Alice", "text": "Check the new paper on ceramides", "ts": "1"},
            {"user": "Bob", "text": "LONI access approved!", "ts": "2"},
        ]
        result = format_inbound_summary(msgs, channel_name="#research")
        assert "#research" in result
        assert "Alice" in result
        assert "ceramides" in result

    def test_truncates_long_messages(self):
        msgs = [{"user": "U1", "text": "x" * 300, "ts": "1"}]
        result = format_inbound_summary(msgs)
        assert "..." in result

    def test_caps_at_ten(self):
        msgs = [{"user": f"U{i}", "text": f"msg {i}", "ts": str(i)} for i in range(15)]
        result = format_inbound_summary(msgs)
        assert "5 more" in result
