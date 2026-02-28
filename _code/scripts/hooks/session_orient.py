"""SessionStart hook: orient the agent to current vault state.

Reads active goals, top hypotheses, latest meta-review, vault state
counts, active threads from goals.md, overdue reminders, and
maintenance signals. Produces a compact orientation block on stdout.

Consolidated from session_orient.py + session-orient.sh.

Usage (Claude Code hook):
    uv run python scripts/hooks/session_orient.py
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_CODE_DIR = _SCRIPT_DIR.parent.parent  # _code/

# Ensure src/ is importable for engram_r package
sys.path.insert(0, str(_CODE_DIR / "src"))

from engram_r.hook_utils import load_config, resolve_vault  # noqa: E402


def _list_active_goals(vault: Path) -> list[str]:
    """List active research goals by reading goal files."""
    goals_dir = vault / "_research" / "goals"
    if not goals_dir.is_dir():
        return []
    goals = []
    for f in sorted(goals_dir.glob("*.md")):
        if f.name.startswith("_"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
            if text.startswith("---"):
                fm_end = text.find("\n---\n", 4)
                if fm_end > 0:
                    fm = yaml.safe_load(text[4:fm_end])
                    if isinstance(fm, dict):
                        status = fm.get("status", "active")
                        if status == "active":
                            title = fm.get("title", f.stem)
                            goals.append(title)
        except Exception:
            continue
    return goals


def _top_hypotheses(vault: Path, n: int = 5) -> list[str]:
    """Extract top N from _research/hypotheses/_index.md leaderboard."""
    index_path = vault / "_research" / "hypotheses" / "_index.md"
    if not index_path.exists():
        return []
    lines = index_path.read_text(encoding="utf-8").splitlines()
    results = []
    in_table = False
    for line in lines:
        if line.startswith("|") and "Rank" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 4:
                rank, hyp_id, title, elo = cells[0], cells[1], cells[2], cells[3]
                results.append(f"  {rank}. {title} (Elo {elo})")
            if len(results) >= n:
                break
        elif in_table and not line.startswith("|"):
            break
    return results


def _latest_meta_review(vault: Path) -> str | None:
    """Find the most recent meta-review and return a summary line."""
    mr_dir = vault / "_research" / "meta-reviews"
    if not mr_dir.is_dir():
        return None
    files = sorted(mr_dir.glob("*.md"), reverse=True)
    if not files:
        return None
    latest = files[0]
    try:
        text = latest.read_text(encoding="utf-8")
        if text.startswith("---"):
            fm_end = text.find("\n---\n", 4)
            if fm_end > 0:
                fm = yaml.safe_load(text[4:fm_end])
                if isinstance(fm, dict):
                    d = fm.get("date", latest.stem)
                    reviewed = fm.get("hypotheses_reviewed", "?")
                    matches = fm.get("matches_analyzed", "?")
                    return (
                        f"  Latest: {d} "
                        f"({reviewed} hypotheses, {matches} matches)"
                    )
    except Exception:
        pass
    return f"  Latest: {latest.stem}"


def _load_methodology(vault: Path) -> str:
    """Load compiled methodology directives for session context."""
    compiled = vault / "ops" / "methodology" / "_compiled.md"
    if not compiled.exists():
        return ""
    text = compiled.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


# --- Absorbed from session-orient.sh ---


def _count_md_files(directory: Path) -> int:
    """Count .md files in a directory (non-recursive, excludes dotfiles and .gitkeep)."""
    if not directory.is_dir():
        return 0
    return sum(
        1
        for f in directory.iterdir()
        if f.suffix == ".md" and not f.name.startswith(".")
    )


def _vault_state_counts(vault: Path) -> dict[str, int]:
    """Count claims, inbox items, observations, and tensions."""
    return {
        "claims": _count_md_files(vault / "notes"),
        "inbox": _count_md_files(vault / "inbox"),
        "observations": _count_md_files(vault / "ops" / "observations"),
        "tensions": _count_md_files(vault / "ops" / "tensions"),
    }


def _goals_md_threads(vault: Path, max_lines: int = 10) -> list[str]:
    """Extract bullet lines from self/goals.md as active threads."""
    goals_file = vault / "self" / "goals.md"
    if not goals_file.exists():
        return []
    try:
        text = goals_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        bullets = [ln for ln in lines if re.match(r"^\s*-\s", ln)]
        return bullets[:max_lines]
    except Exception:
        return []


def _overdue_reminders(vault: Path, max_lines: int = 5) -> list[str]:
    """Extract unchecked reminders from ops/reminders.md."""
    reminders_file = vault / "ops" / "reminders.md"
    if not reminders_file.exists():
        return []
    try:
        text = reminders_file.read_text(encoding="utf-8")
        today_str = date.today().isoformat()
        lines = text.splitlines()
        unchecked = []
        for ln in lines:
            if re.match(r"^\s*- \[ \]", ln):
                # Extract date if present (format: YYYY-MM-DD)
                m = re.search(r"(\d{4}-\d{2}-\d{2})", ln)
                if m and m.group(1) <= today_str:
                    unchecked.append(ln)
                elif not m:
                    # No date -- include as undated reminder
                    unchecked.append(ln)
        return unchecked[:max_lines]
    except Exception:
        return []


def _slack_inbound(vault: Path) -> str:
    """Fetch inbound Slack messages for orientation. Never raises."""
    try:
        from engram_r.slack_notify import fetch_inbound_messages

        return fetch_inbound_messages(vault)
    except Exception:
        return ""


def _slack_session_start(vault: Path, goals: list[str], top: list[str]) -> None:
    """Fire session_start Slack notification. Never raises."""
    try:
        from engram_r.slack_notify import send_notification

        send_notification(
            "session_start",
            vault,
            goals=goals,
            top_hypotheses=top,
        )
    except Exception:
        pass


def main() -> None:
    """Print orientation block to stdout."""
    config = load_config()
    vault = resolve_vault(config)

    # Check .arscontexta marker exists (skip if not an arscontexta vault)
    if not (vault / ".arscontexta").exists():
        return

    parts = ["[Session Orient]"]

    # Active goals
    goals = _list_active_goals(vault)
    if goals:
        parts.append("Active goals:")
        for g in goals:
            parts.append(f"  - {g}")
    else:
        parts.append("Active goals: (none found)")

    # Top hypotheses
    top = _top_hypotheses(vault)
    if top:
        parts.append("Top hypotheses:")
        for line in top:
            parts.append(line)
    else:
        parts.append("Top hypotheses: (no leaderboard)")

    # Meta-review
    mr = _latest_meta_review(vault)
    if mr:
        parts.append("Meta-review:")
        parts.append(mr)
    else:
        parts.append("Meta-review: (none yet)")

    # Active threads from goals.md (absorbed from session-orient.sh)
    threads = _goals_md_threads(vault)
    if threads:
        parts.append("")
        parts.append("### Active Threads")
        for t in threads:
            parts.append(t)

    # Overdue reminders (absorbed from session-orient.sh)
    reminders = _overdue_reminders(vault)
    if reminders:
        parts.append("")
        parts.append("### Reminders")
        for r in reminders:
            parts.append(r)

    # Vault state counts (absorbed from session-orient.sh)
    counts = _vault_state_counts(vault)
    parts.append("")
    parts.append("### Vault State")
    parts.append(
        f"  Claims: {counts['claims']} | "
        f"Inbox: {counts['inbox']} | "
        f"Observations: {counts['observations']} | "
        f"Tensions: {counts['tensions']}"
    )

    # Maintenance signals
    if counts["inbox"] > 0:
        parts.append("  -> Inbox has unprocessed items")
    if counts["observations"] >= 10:
        parts.append("  -> 10+ observations pending -- consider running /rethink")
    if counts["tensions"] >= 5:
        parts.append("  -> 5+ tensions pending -- consider running /rethink")

    # Methodology directives
    methodology = _load_methodology(vault)
    if methodology:
        parts.append("")
        parts.append(methodology)

    # Slack inbound messages
    inbound = _slack_inbound(vault)
    if inbound:
        parts.append("")
        parts.append(inbound)

    print("\n".join(parts))

    # Fire session_start notification (non-blocking, never fails)
    _slack_session_start(vault, goals, top)


if __name__ == "__main__":
    main()
