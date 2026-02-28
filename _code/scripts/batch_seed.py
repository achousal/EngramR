"""Batch-seed literature notes and hypotheses into the processing queue.

Creates task files, archive folders, and queue entries for all sources.
Each source gets an allocated claim number range (30 per source).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

VAULT = Path(os.environ.get(
    "VAULT_ROOT",
    str(Path(__file__).resolve().parents[2])
))
QUEUE_DIR = VAULT / "ops" / "queue"
QUEUE_FILE = QUEUE_DIR / "queue.json"
ARCHIVE_DIR = QUEUE_DIR / "archive"
DATE = "2026-02-22"
CLAIMS_PER_SOURCE = 30

LITERATURE = [
    "_research/literature/2026-bach-immunometabolism-reframes-alzheimers-disease-from.md",
    "_research/literature/2026-eissman-biological-age-acceleration-associates-with-alzhei.md",
    "_research/literature/2026-garcia-gonzalez-csf-turnover-reshapes-biomarker-interpretation-in.md",
    "_research/literature/2026-johnson-clonal-expansion-of-cytotoxic-cd8-t-cells-in-lecan.md",
    "_research/literature/2026-keshavan-the-alzheimers-disease-diagnosis-and-plasma-phosph.md",
    "_research/literature/2026-kwan-peripheral-blood-epigenetic-age-acceleration-is-as.md",
    "_research/literature/2026-lukacsovich-dna-methylation-signature-of-cognitive-reserve-mod.md",
    "_research/literature/2026-wang-akkermansia-muciniphila-reduces-neuroinflammation.md",
    "_research/literature/2026-xu-resolving-cognitive-heterogeneity-in-white-matter.md",
    "_research/literature/2026-yaskolka-brain-peripheral-proteome-crosstalk-in-alzheimers.md",
]

HYPOTHESES = [
    "_research/hypotheses/H001-neuroinflammatory-hub-rewiring.md",
    "_research/hypotheses/H001v2-neuroinflammatory-hub-rewiring.md",
    "_research/hypotheses/H002-metabolic-transcriptomic-entropy.md",
    "_research/hypotheses/H003-controllability-driver-nodes.md",
    "_research/hypotheses/H004-cross-omic-edge-stability-subtypes.md",
    "_research/hypotheses/H005-critical-slowing-down.md",
    "_research/hypotheses/H006-subtype-specific-hub-rewiring.md",
    "_research/hypotheses/H007-negative-control-confounders.md",
    "_research/hypotheses/H008-spectral-wavelet-ssm-architecture.md",
    "_research/hypotheses/H-AD-001-epigenetic-age-acceleration-composite.md",
    "_research/hypotheses/H-AD-001b-epigenetic-age-acceleration-v2.md",
    "_research/hypotheses/H-AD-002-cd8-t-cell-exhaustion-signature.md",
    "_research/hypotheses/H-AD-002b-cd8-t-cell-exhaustion-v2.md",
    "_research/hypotheses/H-AD-003-synaptic-complement-ratio-panel.md",
    "_research/hypotheses/H-AD-003b-synaptic-complement-ratio-v2.md",
    "_research/hypotheses/H-AD-004-ceramide-plasmalogen-ratio.md",
    "_research/hypotheses/H-AD-004b-ceramide-plasmalogen-ratio-v2.md",
    "_research/hypotheses/H-AD-005-cross-omic-correlation-disruption.md",
    "_research/hypotheses/H-AD-006-monocyte-trem2-lipid-sensing.md",
    "_research/hypotheses/H-AD-007-secondary-bile-acid-panel.md",
    "_research/hypotheses/H-AD-008-neural-ev-cargo-signature.md",
]


def count_lines(filepath: Path) -> int:
    """Count lines in a file, return 0 if file doesn't exist."""
    try:
        with open(filepath) as f:
            return sum(1 for _ in f)
    except (FileNotFoundError, UnicodeDecodeError):
        return 0


def detect_content_type(source_path: str) -> str:
    """Detect content type from source path."""
    if source_path.startswith("_research/literature/"):
        return "literature note (co-scientist)"
    elif source_path.startswith("_research/hypotheses/"):
        return "hypothesis (co-scientist)"
    return "unknown"


def create_task_file(
    basename: str,
    source_path: str,
    archive_folder: str,
    claim_start: int,
    line_count: int,
    content_type: str,
    timestamp: str,
) -> str:
    """Generate task file content."""
    return f"""---
id: {basename}
type: extract
source: {source_path}
original_path: {source_path}
archive_folder: {archive_folder}
created: {timestamp}
next_claim_start: {claim_start}
---

# Extract claims from {Path(source_path).name}

## Source
Original: {source_path}
Archived: {source_path} (living doc, stays in place)
Size: {line_count} lines
Content type: {content_type}

## Scope
Full document

## Acceptance Criteria
- Extract claims, implementation ideas, tensions, and testable hypotheses
- Duplicate check against notes/ during extraction
- Near-duplicates create enrichment tasks (do not skip)
- Each output type gets appropriate handling
- For hypothesis sources: extract mechanism claims, predictions, assumptions, limitations
- For literature sources: extract findings, methods, evidence claims

## Execution Notes
(filled by /reduce)

## Outputs
(filled by /reduce)
"""


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Read existing queue
    with open(QUEUE_FILE) as f:
        queue = json.load(f)

    all_sources = LITERATURE + HYPOTHESES
    claim_start = 1
    seeded = []

    for source_path in all_sources:
        basename = Path(source_path).stem
        full_path = VAULT / source_path

        # Verify source exists
        if not full_path.exists():
            # Try with accent characters for garcia-gonzalez
            alt_name = source_path.replace("garcia-gonzalez", "garc\u00eda-gonz\u00e1lez")
            alt_path = VAULT / alt_name
            if alt_path.exists():
                source_path = alt_name
                full_path = alt_path
                basename = Path(source_path).stem
            else:
                print(f"WARN: Source not found: {source_path}")
                continue

        line_count = count_lines(full_path)
        content_type = detect_content_type(source_path)
        archive_folder = f"ops/queue/archive/{DATE}-{basename}"

        # Create archive directory
        archive_path = VAULT / archive_folder
        archive_path.mkdir(parents=True, exist_ok=True)

        # Create task file
        task_content = create_task_file(
            basename=basename,
            source_path=source_path,
            archive_folder=archive_folder,
            claim_start=claim_start,
            line_count=line_count,
            content_type=content_type,
            timestamp=timestamp,
        )
        task_file = QUEUE_DIR / f"{basename}.md"
        with open(task_file, "w") as f:
            f.write(task_content)

        # Add queue entry
        queue["tasks"].append({
            "id": basename,
            "type": "extract",
            "status": "pending",
            "source": source_path,
            "file": f"{basename}.md",
            "created": timestamp,
            "next_claim_start": claim_start,
        })

        seeded.append({
            "id": basename,
            "source": source_path,
            "lines": line_count,
            "type": content_type,
            "claim_start": claim_start,
        })

        claim_start += CLAIMS_PER_SOURCE

    # Write updated queue
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)
        f.write("\n")

    # Report
    lit_count = sum(1 for s in seeded if "literature" in s["type"])
    hyp_count = sum(1 for s in seeded if "hypothesis" in s["type"])
    total_lines = sum(s["lines"] for s in seeded)

    print(f"--=={{ batch seed }}==--")
    print(f"")
    print(f"Seeded: {len(seeded)} sources ({lit_count} literature, {hyp_count} hypotheses)")
    print(f"Total lines: {total_lines}")
    print(f"Claim number range: 001-{claim_start - 1:03d}")
    print(f"Queue file: ops/queue/queue.json")
    print(f"")
    print(f"Sources seeded:")
    for s in seeded:
        print(f"  {s['id']}: {s['lines']} lines, claims start at {s['claim_start']:03d}")
    print(f"")
    print(f"Next steps:")
    print(f"  /ralph {lit_count} --type extract   (literature first)")
    print(f"  /ralph {hyp_count} --type extract   (then hypotheses)")
    print(f"  /ralph {len(seeded)} --type extract  (or all at once)")


if __name__ == "__main__":
    main()
