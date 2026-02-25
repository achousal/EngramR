"""SessionStart hook: orient the agent to current vault state.

Reads active goals, top hypotheses, and latest meta-review to produce
a compact orientation block printed to stdout.

Usage (Claude Code hook):
    uv run python scripts/hooks/session_orient.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_CODE_DIR = _SCRIPT_DIR.parent.parent  # _code/


def _load_config() -> dict:
    """Load _ops/config.yaml from vault root."""
    config_path = _CODE_DIR.parent / "ops" / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def _find_vault_root() -> Path:
    """Walk up from CWD for .arscontexta marker, then git root, then relative."""
    import subprocess

    d = Path.cwd()
    while d != d.parent:
        if (d / ".arscontexta").is_dir():
            return d
        d = d.parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return _CODE_DIR.parent


def _vault_root(config: dict) -> Path:
    """Resolve vault root from config, marker walk-up, or relative path."""
    if "vault_root" in config:
        return Path(config["vault_root"])
    return _find_vault_root()


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
            # Quick parse for title from frontmatter
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
                    date = fm.get("date", latest.stem)
                    reviewed = fm.get("hypotheses_reviewed", "?")
                    matches = fm.get("matches_analyzed", "?")
                    return (
                        f"  Latest: {date} "
                        f"({reviewed} hypotheses, {matches} matches)"
                    )
    except Exception:
        pass
    return f"  Latest: {latest.stem}"


def _slack_inbound(vault: Path) -> str:
    """Fetch inbound Slack messages for orientation. Never raises."""
    try:
        sys.path.insert(0, str(_CODE_DIR / "src"))
        from engram_r.slack_notify import fetch_inbound_messages

        return fetch_inbound_messages(vault)
    except Exception:
        return ""


def _slack_session_start(vault: Path, goals: list[str], top: list[str]) -> None:
    """Fire session_start Slack notification. Never raises."""
    try:
        sys.path.insert(0, str(_CODE_DIR / "src"))
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
    config = _load_config()
    vault = _vault_root(config)

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
