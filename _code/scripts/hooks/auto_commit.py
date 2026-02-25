"""PostToolUse hook (async): auto-commit vault note changes.

Reads tool input from stdin (JSON). If the written file is under a
git-tracked vault directory, stages and commits it with a descriptive
message. Runs asynchronously so it never delays the session.

Usage (Claude Code hook):
    uv run python scripts/hooks/auto_commit.py

Stdin JSON shape:
    {"tool_name": "Write", "tool_input": {"file_path": "..."}}

Exit behavior:
    - Always exits 0. Failures are logged to stderr, never block.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_CODE_DIR = _SCRIPT_DIR.parent.parent

# Vault directories that contain notes worth auto-committing
_TRACKED_DIRS = {
    "hypotheses",
    "literature",
    "experiments",
    "eda-reports",
    "projects",
    "_research",
    "self",
    "ops",
    "_code",
}


def _load_config() -> dict:
    config_path = _CODE_DIR.parent / "ops" / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def _find_vault_root() -> Path:
    """Walk up from CWD for .arscontexta marker, then git root, then relative."""
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


def _is_git_repo(path: Path) -> bool:
    """Check if path is inside a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(path),
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main() -> None:
    try:
        config = _load_config()

        if not config.get("git_auto_commit", True):
            return

        vault = _vault_root(config)

        # Read hook input from stdin
        raw = sys.stdin.read()
        if not raw.strip():
            return
        hook_input = json.loads(raw)

        tool_input = hook_input.get("tool_input", {})
        file_path_str = tool_input.get("file_path", "")

        if not file_path_str:
            return

        file_path = Path(file_path_str).resolve()
        vault_resolved = vault.resolve()

        if not str(file_path).startswith(str(vault_resolved)):
            return

        # Check if file is under a tracked directory
        try:
            rel = file_path.relative_to(vault_resolved)
        except ValueError:
            return

        top_dir = rel.parts[0] if rel.parts else ""
        if top_dir not in _TRACKED_DIRS:
            return

        # Verify vault root has git
        if not _is_git_repo(vault_resolved):
            return

        # Stage and commit
        subprocess.run(
            ["git", "add", str(file_path)],
            cwd=str(vault_resolved),
            capture_output=True,
            check=True,
        )

        commit_msg = f"auto: update {rel}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg, "--no-verify"],
            cwd=str(vault_resolved),
            capture_output=True,
            check=False,  # Don't fail if nothing to commit
        )

    except Exception as exc:
        print(f"auto_commit: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
