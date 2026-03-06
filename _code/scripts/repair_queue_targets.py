"""One-time repair: sync queue.json targets with actual note filenames.

For each done claim task, reads the task file's ## Create section to find
the actual title, then updates queue.json target if it differs.

Also flags phantom entries (marked done but no note exists on disk).

Usage:
    cd _code && uv run python scripts/repair_queue_targets.py [--dry-run]
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
QUEUE_PATH = VAULT / "ops" / "queue" / "queue.json"
NOTES_DIR = VAULT / "notes"


def extract_created_title(task_file: Path) -> str | None:
    """Parse 'Created: [[actual title]]' from task file's ## Create section."""
    if not task_file.exists():
        return None
    content = task_file.read_text()
    match = re.search(r"## Create\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if not match:
        return None
    create_section = match.group(1)
    link_match = re.search(r"Created:\s*\[\[(.+?)\]\]", create_section)
    if not link_match:
        return None
    return link_match.group(1)


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    with open(QUEUE_PATH) as f:
        queue = json.load(f)

    done_claims = [
        (i, t)
        for i, t in enumerate(queue)
        if t.get("type") == "claim"
        and t.get("status") == "done"
        and "create" in (t.get("completed_phases") or [])
    ]

    synced = 0
    phantoms = 0
    already_correct = 0

    for idx, task in done_claims:
        task_file = VAULT / "ops" / "queue" / task["file"]
        actual_title = extract_created_title(task_file)
        old_target = task["target"]

        if actual_title is None:
            # Can't determine actual title from task file
            note_exists = (NOTES_DIR / f"{old_target}.md").exists()
            if not note_exists:
                print(f"PHANTOM  {task['id']}: no Create section and no note on disk")
                phantoms += 1
            continue

        note_path = NOTES_DIR / f"{actual_title}.md"
        if not note_path.exists():
            print(f"PHANTOM  {task['id']}: Created: [[{actual_title[:60]}...]] but file missing")
            phantoms += 1
            continue

        if old_target == actual_title:
            already_correct += 1
            continue

        print(f"SYNC     {task['id']}:")
        print(f"  old: {old_target[:80]}")
        print(f"  new: {actual_title[:80]}")
        if not dry_run:
            queue[idx]["target"] = actual_title
        synced += 1

    print(f"\n--- Summary ---")
    print(f"Done claims checked: {len(done_claims)}")
    print(f"Already correct:     {already_correct}")
    print(f"Synced:              {synced}")
    print(f"Phantoms:            {phantoms}")

    if not dry_run and synced > 0:
        with open(QUEUE_PATH, "w") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"\nqueue.json updated with {synced} target corrections.")
    elif dry_run:
        print(f"\n[dry-run] No changes written. Remove --dry-run to apply.")


if __name__ == "__main__":
    main()
