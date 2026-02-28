"""Tests for scripts/hooks/session_orient.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_HOOKS_DIR = Path(__file__).resolve().parent.parent / "scripts" / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))
import session_orient  # noqa: E402


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Create a minimal vault structure for testing."""
    v = tmp_path / "vault"
    v.mkdir()

    # Arscontexta marker (file, not directory)
    (v / ".arscontexta").write_text("marker", encoding="utf-8")

    # Minimal config
    ops = v / "ops"
    ops.mkdir()
    (ops / "config.yaml").write_text("", encoding="utf-8")

    # Vault state directories
    (v / "notes").mkdir()
    (v / "inbox").mkdir()
    (v / "ops" / "observations").mkdir(parents=True)
    (v / "ops" / "tensions").mkdir(parents=True)
    (v / "self").mkdir()

    # Research dirs (empty but present)
    goals = v / "_research" / "goals"
    goals.mkdir(parents=True)
    hyps = v / "_research" / "hypotheses"
    hyps.mkdir(parents=True)
    mr = v / "_research" / "meta-reviews"
    mr.mkdir(parents=True)

    return v


@pytest.fixture
def compiled_content() -> str:
    """Sample compiled methodology content."""
    return (
        "# Methodology Directives (compiled)\n"
        "\n"
        "Auto-loaded at session start.\n"
        "\n"
        "## Behavioral Rules\n"
        "\n"
        "**Parallel workflow integrity** -- Reduce fans out, reflect fans in.\n"
    )


# --- Methodology loading tests ---


def test_load_methodology_returns_content(vault: Path, compiled_content: str) -> None:
    """When _compiled.md exists with content, return it without H1 header."""
    meth_dir = vault / "ops" / "methodology"
    meth_dir.mkdir(parents=True)
    (meth_dir / "_compiled.md").write_text(compiled_content, encoding="utf-8")

    result = session_orient._load_methodology(vault)
    assert result != ""
    assert "# Methodology Directives" not in result
    assert "## Behavioral Rules" in result
    assert "Parallel workflow integrity" in result


def test_load_methodology_missing_file(vault: Path) -> None:
    """When _compiled.md does not exist, return empty string."""
    result = session_orient._load_methodology(vault)
    assert result == ""


def test_load_methodology_empty_file(vault: Path) -> None:
    """When _compiled.md exists but is empty, return empty string."""
    meth_dir = vault / "ops" / "methodology"
    meth_dir.mkdir(parents=True)
    (meth_dir / "_compiled.md").write_text("", encoding="utf-8")

    result = session_orient._load_methodology(vault)
    assert result == ""


def test_main_includes_methodology(
    vault: Path, compiled_content: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """When _compiled.md exists, main() includes methodology in output."""
    meth_dir = vault / "ops" / "methodology"
    meth_dir.mkdir(parents=True)
    (meth_dir / "_compiled.md").write_text(compiled_content, encoding="utf-8")

    with (
        patch("session_orient.resolve_vault", return_value=vault),
        patch.object(session_orient, "_slack_inbound", return_value=""),
        patch.object(session_orient, "_slack_session_start"),
    ):
        session_orient.main()

    output = capsys.readouterr().out
    assert "## Behavioral Rules" in output
    assert "Parallel workflow integrity" in output


def test_main_without_methodology(
    vault: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When _compiled.md is absent, main() still produces valid output."""
    with (
        patch("session_orient.resolve_vault", return_value=vault),
        patch.object(session_orient, "_slack_inbound", return_value=""),
        patch.object(session_orient, "_slack_session_start"),
    ):
        session_orient.main()

    output = capsys.readouterr().out
    assert "[Session Orient]" in output
    assert "Active goals:" in output
    assert "Behavioral Rules" not in output


# --- Vault state counts tests (absorbed from session-orient.sh) ---


def test_vault_state_counts_empty(vault: Path) -> None:
    """Empty vault directories return zero counts."""
    counts = session_orient._vault_state_counts(vault)
    assert counts["claims"] == 0
    assert counts["inbox"] == 0
    assert counts["observations"] == 0
    assert counts["tensions"] == 0


def test_vault_state_counts_with_files(vault: Path) -> None:
    """Counts .md files correctly, excludes dotfiles."""
    (vault / "notes" / "claim1.md").write_text("c1", encoding="utf-8")
    (vault / "notes" / "claim2.md").write_text("c2", encoding="utf-8")
    (vault / "notes" / ".hidden.md").write_text("x", encoding="utf-8")
    (vault / "inbox" / "item.md").write_text("i", encoding="utf-8")
    (vault / "ops" / "observations" / "obs.md").write_text("o", encoding="utf-8")

    counts = session_orient._vault_state_counts(vault)
    assert counts["claims"] == 2
    assert counts["inbox"] == 1
    assert counts["observations"] == 1
    assert counts["tensions"] == 0


def test_vault_state_counts_missing_dirs(tmp_path: Path) -> None:
    """Missing directories return zero, no error."""
    counts = session_orient._vault_state_counts(tmp_path)
    assert counts == {"claims": 0, "inbox": 0, "observations": 0, "tensions": 0}


# --- Goals.md threads tests ---


def test_goals_md_threads(vault: Path) -> None:
    """Extracts bullet lines from goals.md."""
    (vault / "self" / "goals.md").write_text(
        "# Goals\n\n- Thread one\n- Thread two\nNot a bullet\n",
        encoding="utf-8",
    )
    threads = session_orient._goals_md_threads(vault)
    assert len(threads) == 2
    assert "- Thread one" in threads[0]


def test_goals_md_threads_missing(vault: Path) -> None:
    """Missing goals.md returns empty list."""
    threads = session_orient._goals_md_threads(vault)
    assert threads == []


# --- Overdue reminders tests ---


def test_overdue_reminders(vault: Path) -> None:
    """Extracts overdue unchecked reminders by date comparison."""
    (vault / "ops" / "reminders.md").write_text(
        "# Reminders\n"
        "- [ ] 2020-01-01: Old overdue task\n"
        "- [x] 2020-01-02: Completed task\n"
        "- [ ] 2099-12-31: Future task\n",
        encoding="utf-8",
    )
    result = session_orient._overdue_reminders(vault)
    assert len(result) == 1
    assert "Old overdue" in result[0]


def test_overdue_reminders_missing(vault: Path) -> None:
    """Missing reminders file returns empty list."""
    result = session_orient._overdue_reminders(vault)
    assert result == []


# --- Main output includes vault state (integration) ---


def test_main_includes_vault_state(
    vault: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Main output includes vault state counts and maintenance signals."""
    (vault / "notes" / "a.md").write_text("x", encoding="utf-8")
    (vault / "inbox" / "b.md").write_text("x", encoding="utf-8")

    with (
        patch("session_orient.resolve_vault", return_value=vault),
        patch.object(session_orient, "_slack_inbound", return_value=""),
        patch.object(session_orient, "_slack_session_start"),
    ):
        session_orient.main()

    output = capsys.readouterr().out
    assert "Claims: 1" in output
    assert "Inbox: 1" in output
    assert "Inbox has unprocessed items" in output
