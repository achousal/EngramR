"""Stop hook: capture session summary to _ops/sessions/.

Extracts key information from the session and writes a compact
summary note. Never fails the session -- all exceptions are caught.

Usage (Claude Code hook):
    uv run python scripts/hooks/session_capture.py

Stdin JSON shape:
    {"transcript_path": "...", "session_id": "..."}

Exit behavior:
    - Always exits 0. Never blocks or fails the session.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_CODE_DIR = _SCRIPT_DIR.parent.parent


def _load_config() -> dict:
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
    if "vault_root" in config:
        return Path(config["vault_root"])
    return _find_vault_root()


def _extract_session_info(hook_input: dict) -> dict:
    """Extract summary info from hook input and transcript."""
    info: dict = {
        "session_id": hook_input.get("session_id", "unknown"),
        "files_written": [],
        "skills_invoked": [],
        "summary": "",
    }

    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path or not Path(transcript_path).exists():
        return info

    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()

        files = set()
        skills = set()
        last_assistant = ""

        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Track file writes
            if isinstance(entry, dict):
                tool_name = entry.get("tool_name", "")
                tool_input = entry.get("tool_input", {})
                if isinstance(tool_input, dict):
                    fp = tool_input.get("file_path", "")
                    if fp and tool_name in ("Write", "Edit"):
                        files.add(fp)

                # Track skill invocations
                if tool_name == "Skill":
                    skill = tool_input.get("skill", "")
                    if skill:
                        skills.add(f"/{skill}")

                # Track last assistant message
                role = entry.get("role", "")
                if role == "assistant":
                    content = entry.get("content", "")
                    if isinstance(content, str) and content.strip():
                        last_assistant = content.strip()

        info["files_written"] = sorted(files)
        info["skills_invoked"] = sorted(skills)
        # Truncate last assistant message
        if len(last_assistant) > 300:
            last_assistant = last_assistant[:300] + "..."
        info["summary"] = last_assistant

    except Exception:
        pass

    return info


def _slack_session_end(vault: Path, info: dict) -> None:
    """Fire session_end Slack notification. Never raises."""
    try:
        sys.path.insert(0, str(_CODE_DIR / "src"))
        from engram_r.slack_notify import send_notification

        send_notification(
            "session_end",
            vault,
            session_id=info.get("session_id", ""),
            files_written=info.get("files_written", []),
            skills_invoked=info.get("skills_invoked", []),
            summary=info.get("summary", ""),
        )
    except Exception:
        pass


def main() -> None:
    try:
        config = _load_config()

        if not config.get("session_capture", True):
            return

        vault = _vault_root(config)

        raw = sys.stdin.read()
        if not raw.strip():
            return

        hook_input = json.loads(raw)
        info = _extract_session_info(hook_input)

        sessions_dir = vault / "ops" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        today = date.today().isoformat()
        session_prefix = info["session_id"][:8] if info["session_id"] else "unknown"
        filename = f"{today}-{session_prefix}.md"
        output_path = sessions_dir / filename

        # Build session note
        parts = [
            "---",
            f"date: {today}",
            f"session_id: {info['session_id']}",
            "---",
            "",
            "## Files Written",
        ]

        if info["files_written"]:
            for fp in info["files_written"]:
                parts.append(f"- `{fp}`")
        else:
            parts.append("(none)")

        parts.append("")
        parts.append("## Skills Invoked")

        if info["skills_invoked"]:
            for s in info["skills_invoked"]:
                parts.append(f"- {s}")
        else:
            parts.append("(none)")

        parts.append("")
        parts.append("## Session Summary")
        parts.append(info["summary"] or "(no summary available)")
        parts.append("")

        output_path.write_text("\n".join(parts), encoding="utf-8")

        # Fire session_end notification (non-blocking, never fails)
        _slack_session_end(vault, info)

    except Exception:
        # Never fail the session
        pass


if __name__ == "__main__":
    main()
