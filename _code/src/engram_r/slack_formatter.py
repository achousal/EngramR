"""Slack Block Kit message formatters for EngramR events.

Pure functions that return (text, blocks) tuples for each notification type.
text is the fallback/notification preview; blocks provide rich formatting.
"""

from __future__ import annotations

from typing import Any


def _header_block(text: str) -> dict[str, Any]:
    """Create a header block."""
    return {"type": "header", "text": {"type": "plain_text", "text": text}}


def _section_block(mrkdwn: str) -> dict[str, Any]:
    """Create a section block with mrkdwn text."""
    return {"type": "section", "text": {"type": "mrkdwn", "text": mrkdwn}}


def _context_block(elements: list[str]) -> dict[str, Any]:
    """Create a context block with mrkdwn elements."""
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": t} for t in elements],
    }


def _divider_block() -> dict[str, Any]:
    """Create a divider block."""
    return {"type": "divider"}


def format_daily_parent(date_str: str) -> tuple[str, list[dict[str, Any]]]:
    """Format the daily parent message that threads all notifications.

    Args:
        date_str: Date string (e.g. '2026-02-23').

    Returns:
        (text, blocks) tuple.
    """
    text = f"EngramR Activity -- {date_str}"
    blocks = [
        _header_block(f"EngramR Activity -- {date_str}"),
        _section_block("All vault notifications for today thread below."),
    ]
    return text, blocks


def format_session_start(
    goals: list[str] | None = None,
    vault_stats: dict[str, Any] | None = None,
    top_hypotheses: list[str] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Format a session start notification.

    Args:
        goals: Active research goal names.
        vault_stats: Dict with keys like 'claims', 'inbox', 'hypotheses'.
        top_hypotheses: Top-ranked hypothesis titles.

    Returns:
        (text, blocks) tuple.
    """
    text = "Session started"
    blocks: list[dict[str, Any]] = [_section_block("*Session started*")]

    stats = vault_stats or {}
    stat_parts = []
    if stats.get("claims"):
        stat_parts.append(f"Claims: {stats['claims']}")
    if stats.get("inbox"):
        stat_parts.append(f"Inbox: {stats['inbox']}")
    if stats.get("hypotheses"):
        stat_parts.append(f"Hypotheses: {stats['hypotheses']}")
    if stat_parts:
        blocks.append(_context_block([" | ".join(stat_parts)]))

    if goals:
        goal_lines = "\n".join(f"- {g}" for g in goals[:5])
        blocks.append(_section_block(f"*Active goals:*\n{goal_lines}"))

    if top_hypotheses:
        hyp_lines = "\n".join(top_hypotheses[:5])
        blocks.append(_section_block(f"*Top hypotheses:*\n{hyp_lines}"))

    return text, blocks


def format_session_end(
    session_id: str = "",
    files_written: list[str] | None = None,
    skills_invoked: list[str] | None = None,
    summary: str = "",
    duration_s: int = 0,
) -> tuple[str, list[dict[str, Any]]]:
    """Format a session end notification.

    Args:
        session_id: Short session ID.
        files_written: List of file paths written during the session.
        skills_invoked: List of skills used (e.g. ['/generate', '/tournament']).
        summary: Brief session summary.
        duration_s: Session duration in seconds.

    Returns:
        (text, blocks) tuple.
    """
    duration_str = _format_duration(duration_s) if duration_s > 0 else ""
    text = f"Session ended ({session_id[:8]})"

    blocks: list[dict[str, Any]] = [_section_block("*Session ended*")]

    ctx_parts = []
    if session_id:
        ctx_parts.append(f"ID: `{session_id[:8]}`")
    if duration_str:
        ctx_parts.append(f"Duration: {duration_str}")
    files = files_written or []
    if files:
        ctx_parts.append(f"Files: {len(files)}")
    if ctx_parts:
        blocks.append(_context_block([" | ".join(ctx_parts)]))

    skills = skills_invoked or []
    if skills:
        blocks.append(_section_block(f"*Skills:* {', '.join(skills)}"))

    if summary:
        truncated = summary[:500] + "..." if len(summary) > 500 else summary
        blocks.append(_section_block(f"*Summary:* {truncated}"))

    return text, blocks


def format_daemon_task_complete(
    skill: str = "",
    task_key: str = "",
    model: str = "",
    elapsed_s: int = 0,
) -> tuple[str, list[dict[str, Any]]]:
    """Format a daemon task completion notification.

    Args:
        skill: Skill that was executed (e.g. 'tournament').
        task_key: Unique task identifier.
        model: Model used (e.g. 'sonnet').
        elapsed_s: Execution time in seconds.

    Returns:
        (text, blocks) tuple.
    """
    duration_str = _format_duration(elapsed_s) if elapsed_s > 0 else ""
    text = f"Daemon: {skill} completed ({task_key})"

    blocks: list[dict[str, Any]] = [
        _section_block(f"*Daemon task completed:* `{skill}`"),
    ]

    ctx_parts = []
    if task_key:
        ctx_parts.append(f"Key: `{task_key}`")
    if model:
        ctx_parts.append(f"Model: {model}")
    if duration_str:
        ctx_parts.append(duration_str)
    if ctx_parts:
        blocks.append(_context_block([" | ".join(ctx_parts)]))

    return text, blocks


def format_daemon_alert(
    message: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    """Format a daemon alert notification.

    Args:
        message: Alert message text.

    Returns:
        (text, blocks) tuple.
    """
    text = f"Daemon alert: {message}"
    blocks: list[dict[str, Any]] = [
        _section_block(f"*Daemon alert*\n{message}"),
    ]
    return text, blocks


def format_daemon_for_you(
    entries: list[str] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Format daemon 'For You' items (queued for human review).

    Args:
        entries: List of entry descriptions.

    Returns:
        (text, blocks) tuple.
    """
    items = entries or []
    text = f"Daemon: {len(items)} item(s) for your review"
    blocks: list[dict[str, Any]] = [
        _section_block(f"*For You* -- {len(items)} item(s) queued for review"),
    ]
    if items:
        item_text = "\n".join(f"- {e}" for e in items[:10])
        blocks.append(_section_block(item_text))
    return text, blocks


def format_tournament_result(
    goal_id: str = "",
    matches: int = 0,
    top_hypotheses: list[str] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Format a tournament result notification.

    Args:
        goal_id: Research goal identifier.
        matches: Number of matches completed.
        top_hypotheses: Top-ranked hypothesis titles after the tournament.

    Returns:
        (text, blocks) tuple.
    """
    text = f"Tournament: {matches} matches for {goal_id}"
    blocks: list[dict[str, Any]] = [
        _section_block(f"*Tournament results* -- `{goal_id}`"),
    ]

    ctx_parts = [f"Matches: {matches}"]
    blocks.append(_context_block(ctx_parts))

    hyps = top_hypotheses or []
    if hyps:
        hyp_text = "\n".join(hyps[:5])
        blocks.append(_section_block(f"*Leaderboard:*\n{hyp_text}"))

    return text, blocks


def format_meta_review(
    goal_id: str = "",
    hypotheses_reviewed: int = 0,
    matches_analyzed: int = 0,
    key_patterns: list[str] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Format a meta-review completion notification.

    Args:
        goal_id: Research goal identifier.
        hypotheses_reviewed: Number of hypotheses reviewed.
        matches_analyzed: Number of tournament matches analyzed.
        key_patterns: Key patterns extracted.

    Returns:
        (text, blocks) tuple.
    """
    text = (
        f"Meta-review: {goal_id}"
        f" ({hypotheses_reviewed} hyps, {matches_analyzed} matches)"
    )
    blocks: list[dict[str, Any]] = [
        _section_block(f"*Meta-review completed* -- `{goal_id}`"),
    ]

    ctx_parts = [
        f"Hypotheses: {hypotheses_reviewed}",
        f"Matches: {matches_analyzed}",
    ]
    blocks.append(_context_block(ctx_parts))

    patterns = key_patterns or []
    if patterns:
        pattern_text = "\n".join(f"- {p}" for p in patterns[:5])
        blocks.append(_section_block(f"*Key patterns:*\n{pattern_text}"))

    return text, blocks


def format_inbound_summary(
    messages: list[dict[str, str]],
    channel_name: str = "",
) -> str:
    """Format inbound Slack messages for session orientation.

    Args:
        messages: List of dicts with 'user', 'text', 'ts' keys.
        channel_name: Name of the channel for display.

    Returns:
        Plain text summary for inclusion in the orientation block.
    """
    if not messages:
        return ""

    header = f"Slack messages ({channel_name})" if channel_name else "Slack messages"
    lines = [header]
    for msg in messages[:10]:
        user = msg.get("user", "unknown")
        text = msg.get("text", "")
        # Truncate long messages
        if len(text) > 200:
            text = text[:200] + "..."
        lines.append(f"  [{user}] {text}")

    if len(messages) > 10:
        lines.append(f"  ... and {len(messages) - 10} more")

    return "\n".join(lines)


def _format_duration(seconds: int) -> str:
    """Format seconds into a human-readable duration string."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    remaining = seconds % 60
    if minutes < 60:
        return f"{minutes}m {remaining}s" if remaining else f"{minutes}m"
    hours = minutes // 60
    remaining_min = minutes % 60
    return f"{hours}h {remaining_min}m"
