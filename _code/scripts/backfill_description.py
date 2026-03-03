"""One-shot backfill: add description field to literature, research-goal, and project notes.

Also appends a Topics section to the body if missing.
Run once from _code/, then delete this script.

Usage:
    uv run python scripts/backfill_description.py --vault-root ..
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

_FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Directories to scan and their note types
SCAN_TARGETS = [
    ("_research/literature", "literature"),
    ("_research/goals", "research-goal"),
    ("projects", "project"),
]


def _derive_description(fm: dict, body: str, note_type: str) -> str:
    """Auto-derive a description from note content."""
    if note_type == "literature":
        # Extract first sentence of abstract
        abstract_match = re.search(
            r"## Abstract\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL
        )
        if abstract_match:
            abstract_text = abstract_match.group(1).strip()
            if abstract_text:
                first_sentence = abstract_text.split(". ")[0]
                if not first_sentence.endswith("."):
                    first_sentence += "."
                return first_sentence[:150]
        return ""

    if note_type == "research-goal":
        # Extract objective section
        obj_match = re.search(
            r"## Objective\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL
        )
        if obj_match:
            obj_text = obj_match.group(1).strip()
            if obj_text:
                first_sentence = obj_text.split(". ")[0]
                if not first_sentence.endswith("."):
                    first_sentence += "."
                return first_sentence[:150]
        return ""

    if note_type == "project":
        # Extract first line of Description section or body
        desc_match = re.search(
            r"## Description\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL
        )
        if desc_match:
            desc_text = desc_match.group(1).strip()
            if desc_text:
                first_line = desc_text.split("\n")[0].strip()
                return first_line[:150]
        return ""

    return ""


def _has_topics_section(body: str) -> bool:
    """Check if body has a Topics section."""
    return bool(re.search(r"^Topics:\s*$", body, re.MULTILINE))


def backfill_file(filepath: Path, note_type: str, dry_run: bool = False) -> dict:
    """Backfill a single file. Returns a status dict."""
    content = filepath.read_text()
    fm_match = _FM_PATTERN.match(content)
    if not fm_match:
        return {"path": str(filepath), "status": "skip", "reason": "no frontmatter"}

    fm_text = fm_match.group(1)
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return {"path": str(filepath), "status": "skip", "reason": "bad yaml"}

    if not isinstance(fm, dict):
        return {"path": str(filepath), "status": "skip", "reason": "not a dict"}

    actual_type = fm.get("type", "")
    if actual_type != note_type:
        return {"path": str(filepath), "status": "skip", "reason": f"type={actual_type}"}

    changes = []
    body = content[fm_match.end():]

    # Check if description needs adding
    needs_description = "description" not in fm
    if needs_description:
        desc = _derive_description(fm, body, note_type)
        fm["description"] = desc
        changes.append(f"added description: {desc[:60]}..." if len(desc) > 60 else f"added description: {desc}")

    # Check if Topics section needs adding
    needs_topics = not _has_topics_section(body)
    if needs_topics:
        # Append Topics section
        body = body.rstrip() + "\n\n---\n\nTopics:\n"
        changes.append("added Topics section")

    if not changes:
        return {"path": str(filepath), "status": "ok", "reason": "already complete"}

    if dry_run:
        return {"path": str(filepath), "status": "would_update", "changes": changes}

    # Rebuild content with updated frontmatter
    new_fm_str = yaml.dump(
        fm, default_flow_style=False, sort_keys=False, allow_unicode=True
    ).rstrip()
    new_content = f"---\n{new_fm_str}\n---\n\n{body}"
    filepath.write_text(new_content)
    return {"path": str(filepath), "status": "updated", "changes": changes}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill description + Topics")
    parser.add_argument("--vault-root", required=True, help="Vault root directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    args = parser.parse_args()

    vault = Path(args.vault_root).resolve()
    stats = {"updated": 0, "skipped": 0, "ok": 0, "errors": 0}

    for rel_dir, note_type in SCAN_TARGETS:
        scan_dir = vault / rel_dir
        if not scan_dir.exists():
            print(f"SKIP: {scan_dir} does not exist")
            continue

        for md_file in sorted(scan_dir.rglob("*.md")):
            result = backfill_file(md_file, note_type, dry_run=args.dry_run)
            status = result["status"]

            if status == "updated" or status == "would_update":
                stats["updated"] += 1
                changes = ", ".join(result.get("changes", []))
                print(f"  {'WOULD ' if args.dry_run else ''}UPDATE: {md_file.name} -- {changes}")
            elif status == "ok":
                stats["ok"] += 1
            elif status == "skip":
                stats["skipped"] += 1
            else:
                stats["errors"] += 1

    print(f"\nSummary: {stats['updated']} updated, {stats['ok']} already ok, "
          f"{stats['skipped']} skipped, {stats['errors']} errors")

    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
