"""PostToolUse hook (sync): validate note schema on Write/Edit.

Reads tool input from stdin (JSON). If the written file is a vault note
with YAML frontmatter containing a known ``type:``, validates against
the schema. Blocks the write on failure.

Usage (Claude Code hook):
    uv run python scripts/hooks/validate_write.py

Stdin JSON shape:
    {"tool_name": "Write", "tool_input": {"file_path": "...", "content": "..."}}

Exit behavior:
    - Print JSON with ``"decision": "block"`` on validation failure.
    - Exit 0 silently on success or non-note files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

# Add src to path so we can import schema_validator
_SCRIPT_DIR = Path(__file__).resolve().parent
_CODE_DIR = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_CODE_DIR / "src"))

from engram_r.schema_validator import validate_filename, validate_note  # noqa: E402

# Directories where notes are flat (no subdirectories allowed).
# A write to notes/subdir/file.md indicates a / in the title.
_FLAT_DIRS = {"notes", "hypotheses", "literature", "experiments"}


def _check_flat_dir_violation(rel_path: str) -> str | None:
    """Return an error message if rel_path nests inside a flat directory.

    For example, ``notes/APP/PS1 mice.md`` is a violation because ``notes/``
    must be flat. The ``/`` in ``APP/PS1`` created an accidental subdirectory.
    """
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) >= 3 and parts[0] in _FLAT_DIRS:
        # Expected: notes/filename.md (2 parts). 3+ means nesting.
        return (
            f"Filename contains '/' which creates subdirectories: {rel_path}. "
            f"Replace '/' with '-' in the note title "
            f"(e.g., 'APP/PS1' -> 'APP-PS1')."
        )
    return None


def _load_config() -> dict:
    """Load _ops/config.yaml."""
    config_path = _CODE_DIR.parent / "ops" / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def _find_vault_root() -> Path:
    """Walk up from CWD for .arscontexta marker, then git root, then relative."""
    import subprocess

    cwd = Path.cwd()
    d = cwd
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


def main() -> None:
    """Validate a written file against note schemas."""
    config = _load_config()

    # Check if validation is enabled
    if not config.get("schema_validation", True):
        return

    vault = _vault_root(config)

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        hook_input = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        return

    tool_input = hook_input.get("tool_input", {})
    file_path_str = tool_input.get("file_path", "")

    if not file_path_str:
        return

    file_path = Path(file_path_str)

    # Only validate .md files under vault root
    if file_path.suffix != ".md":
        return

    try:
        vault_resolved = vault.resolve()
        file_resolved = file_path.resolve()
        if not str(file_resolved).startswith(str(vault_resolved)):
            return
    except Exception:
        return

    # Skip files in _code/ (code, templates, and styles -- not notes)
    try:
        rel = file_resolved.relative_to(vault_resolved)
        rel_str = str(rel)
        if rel_str.startswith("_code"):
            return
    except ValueError:
        return

    # Check for / in note titles (creates accidental subdirectories)
    flat_error = _check_flat_dir_violation(rel_str)
    if flat_error:
        response = {
            "decision": "block",
            "reason": flat_error,
        }
        print(json.dumps(response))
        sys.exit(0)

    # Check for other unsafe characters (: * ? " < > |) in the filename
    filename_errors = validate_filename(rel_str)
    if filename_errors:
        response = {
            "decision": "block",
            "reason": "; ".join(filename_errors),
        }
        print(json.dumps(response))
        sys.exit(0)

    # Read the content -- prefer tool_input content if available (Write),
    # otherwise read from disk (Edit)
    content = tool_input.get("content", "")
    if not content and file_path.exists():
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return

    if not content:
        return

    result = validate_note(content)

    if not result.valid:
        response = {
            "decision": "block",
            "reason": "; ".join(result.errors),
        }
        print(json.dumps(response))
        sys.exit(0)


if __name__ == "__main__":
    main()
