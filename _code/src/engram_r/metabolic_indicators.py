"""Metabolic indicators for daemon self-regulation.

Computes 5 derived metrics from vault state that govern whether the daemon
should create (generate/evolve) or consolidate (reflect/reweave/verify).

Pure Python -- no network I/O. Reuses existing vault filesystem conventions.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _read_frontmatter(path: Path) -> dict:
    """Read YAML frontmatter from a markdown file. Returns {} on failure."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return {}
    m = _FM_RE.match(text)
    if not m:
        return {}
    try:
        fm = yaml.safe_load(m.group(1))
        return fm if isinstance(fm, dict) else {}
    except yaml.YAMLError:
        return {}


@dataclass
class MetabolicState:
    """Snapshot of 5 metabolic indicators plus alarm classification.

    Attributes:
        qpr: Queue Pressure Ratio -- days of backlog at current processing rate.
        vdr: Verification Debt Ratio -- % of claims not human-verified.
        cmr: Creation:Maintenance Ratio -- new notes vs maintained per week.
        hcr: Hypothesis Conversion Rate -- % with empirical engagement.
        swr: Session Waste Ratio -- sessions per useful artifact.
        alarm_keys: Which indicators are in alarm state.
    """

    qpr: float = 0.0
    vdr: float = 0.0
    cmr: float = 0.0
    hcr: float = 0.0
    swr: float = 0.0
    alarm_keys: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Individual indicator computations
# ---------------------------------------------------------------------------


def compute_qpr(
    queue_data: dict | None = None,
    queue_path: Path | None = None,
    lookback_days: int = 7,
) -> float:
    """Compute Queue Pressure Ratio: days of backlog at current rate.

    Args:
        queue_data: Pre-loaded queue.json dict, or None to read from disk.
        queue_path: Path to queue.json (used if queue_data is None).
        lookback_days: Window for computing daily completion rate.

    Returns:
        QPR value (days of backlog). Higher = more pressure.
    """
    if queue_data is None:
        if queue_path is None or not queue_path.is_file():
            return 0.0
        try:
            queue_data = json.loads(queue_path.read_text())
        except (json.JSONDecodeError, OSError):
            return 0.0

    tasks = queue_data.get("tasks", [])
    if not tasks:
        return 0.0

    backlog = sum(1 for t in tasks if t.get("status") not in ("done", "archived"))
    if backlog == 0:
        return 0.0

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    completed_recent = 0
    for t in tasks:
        completed_str = t.get("completed")
        if not completed_str:
            continue
        try:
            completed_dt = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
            if completed_dt >= cutoff:
                completed_recent += 1
        except (ValueError, TypeError):
            continue

    daily_rate = max(completed_recent / lookback_days, 0.1)
    return backlog / daily_rate


def compute_vdr(notes_dir: Path) -> float:
    """Compute Verification Debt Ratio: % of claims not human-verified.

    Args:
        notes_dir: Path to notes/ directory.

    Returns:
        VDR as percentage (0-100). Higher = more debt.
    """
    if not notes_dir.is_dir():
        return 0.0

    total = 0
    human_verified = 0
    for f in notes_dir.iterdir():
        if f.suffix != ".md" or f.name == "_index.md":
            continue
        total += 1
        fm = _read_frontmatter(f)
        if fm.get("verified_by") == "human":
            human_verified += 1

    if total == 0:
        return 0.0
    return (total - human_verified) / total * 100


def compute_cmr(
    notes_dir: Path,
    queue_data: dict | None = None,
    queue_path: Path | None = None,
    lookback_days: int = 7,
) -> float:
    """Compute Creation:Maintenance Ratio over the lookback window.

    Creation = notes with `created` date in last N days.
    Maintenance = queue tasks with type "claim" and completed_phases
    containing "reflect" or "reweave", completed in last N days.

    Args:
        notes_dir: Path to notes/ directory.
        queue_data: Pre-loaded queue.json dict.
        queue_path: Path to queue.json (used if queue_data is None).
        lookback_days: Window for rate computations.

    Returns:
        CMR value. Higher = more creation-heavy.
    """
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    cutoff_date = cutoff.date()

    # Count recent creations
    creation = 0
    if notes_dir.is_dir():
        for f in notes_dir.iterdir():
            if f.suffix != ".md" or f.name == "_index.md":
                continue
            fm = _read_frontmatter(f)
            created_str = fm.get("created", "")
            if created_str:
                try:
                    created_date = datetime.fromisoformat(str(created_str)).date()
                    if created_date >= cutoff_date:
                        creation += 1
                        continue
                except (ValueError, TypeError):
                    pass
            # Fallback: file ctime
            try:
                ctime = datetime.fromtimestamp(f.stat().st_ctime, tz=UTC)
                if ctime >= cutoff:
                    creation += 1
            except OSError:
                pass

    # Count recent maintenance completions
    if queue_data is None:
        if queue_path is not None and queue_path.is_file():
            try:
                queue_data = json.loads(queue_path.read_text())
            except (json.JSONDecodeError, OSError):
                queue_data = {"tasks": []}
        else:
            queue_data = {"tasks": []}

    maintenance = 0
    for t in queue_data.get("tasks", []):
        if t.get("type") != "claim":
            continue
        phases = t.get("completed_phases", [])
        if not isinstance(phases, list):
            continue
        if not any(p in phases for p in ("reflect", "reweave")):
            continue
        completed_str = t.get("completed")
        if not completed_str:
            continue
        try:
            completed_dt = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
            if completed_dt >= cutoff:
                maintenance += 1
        except (ValueError, TypeError):
            continue

    return max(creation, 1) / max(maintenance, 1)


def compute_hcr(hypotheses_dir: Path) -> float:
    """Compute Hypothesis Conversion Rate: % with empirical engagement.

    Converted = status in {tested-positive, tested-negative, executing,
    sap-written}.

    Args:
        hypotheses_dir: Path to _research/hypotheses/ directory.

    Returns:
        HCR as percentage (0-100). Higher = more hypotheses tested.
    """
    if not hypotheses_dir.is_dir():
        return 0.0

    converted_statuses = {
        "tested-positive",
        "tested-negative",
        "executing",
        "sap-written",
    }

    total = 0
    converted = 0
    for f in hypotheses_dir.iterdir():
        if f.suffix != ".md" or f.name.startswith("_"):
            continue
        fm = _read_frontmatter(f)
        if fm.get("type") != "hypothesis":
            continue
        total += 1
        status = str(fm.get("status", "")).strip()
        if status in converted_statuses:
            converted += 1

    if total == 0:
        return 0.0
    return converted / total * 100


def compute_swr(
    sessions_dir: Path,
    notes_dir: Path,
    hypotheses_dir: Path,
) -> float:
    """Compute Session Waste Ratio: sessions per useful artifact.

    Args:
        sessions_dir: Path to ops/sessions/ directory.
        notes_dir: Path to notes/ directory.
        hypotheses_dir: Path to _research/hypotheses/ directory.

    Returns:
        SWR value. Higher = more sessions per artifact.
    """
    session_count = 0
    if sessions_dir.is_dir():
        for f in sessions_dir.iterdir():
            if f.suffix == ".md":
                session_count += 1

    artifact_count = 0
    if notes_dir.is_dir():
        artifact_count += sum(
            1
            for f in notes_dir.iterdir()
            if f.suffix == ".md" and f.name != "_index.md"
        )
    if hypotheses_dir.is_dir():
        artifact_count += sum(
            1
            for f in hypotheses_dir.iterdir()
            if f.suffix == ".md" and not f.name.startswith("_")
        )

    return session_count / max(artifact_count, 1)


# ---------------------------------------------------------------------------
# Alarm classification
# ---------------------------------------------------------------------------


def classify_alarms(
    state: MetabolicState,
    *,
    qpr_critical: float = 3.0,
    cmr_hot: float = 10.0,
    hcr_redirect: float = 15.0,
    swr_archive: float = 5.0,
) -> list[str]:
    """Classify which metabolic indicators are in alarm state.

    Args:
        state: Computed metabolic state.
        qpr_critical: QPR threshold for generation halt.
        cmr_hot: CMR threshold for running hot.
        hcr_redirect: HCR threshold (below = redirect to SAP).
        swr_archive: SWR threshold for stub archival.

    Returns:
        List of alarm keys (e.g. ["qpr_critical", "cmr_hot"]).
    """
    alarms: list[str] = []
    if state.qpr > qpr_critical:
        alarms.append("qpr_critical")
    if state.cmr > cmr_hot:
        alarms.append("cmr_hot")
    if state.hcr < hcr_redirect:
        alarms.append("hcr_low")
    if state.swr > swr_archive:
        alarms.append("swr_high")
    # VDR is informational only (95%+ is current reality)
    return alarms


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_metabolic_state(
    vault_path: Path,
    queue_data: dict | None = None,
    lookback_days: int = 7,
    qpr_critical: float = 3.0,
    cmr_hot: float = 10.0,
    hcr_redirect: float = 15.0,
    swr_archive: float = 5.0,
) -> MetabolicState:
    """Compute all 5 metabolic indicators from vault filesystem.

    Args:
        vault_path: Root of the Obsidian vault.
        queue_data: Pre-loaded queue.json dict, or None to read from disk.
        lookback_days: Window for rate computations.
        qpr_critical: QPR alarm threshold.
        cmr_hot: CMR alarm threshold.
        hcr_redirect: HCR alarm threshold (below triggers).
        swr_archive: SWR alarm threshold.

    Returns:
        Populated MetabolicState with alarm classification.
    """
    notes_dir = vault_path / "notes"
    hypotheses_dir = vault_path / "_research" / "hypotheses"
    sessions_dir = vault_path / "ops" / "sessions"
    queue_path = vault_path / "ops" / "queue" / "queue.json"

    state = MetabolicState(
        qpr=compute_qpr(
            queue_data=queue_data,
            queue_path=queue_path,
            lookback_days=lookback_days,
        ),
        vdr=compute_vdr(notes_dir),
        cmr=compute_cmr(
            notes_dir=notes_dir,
            queue_data=queue_data,
            queue_path=queue_path,
            lookback_days=lookback_days,
        ),
        hcr=compute_hcr(hypotheses_dir),
        swr=compute_swr(sessions_dir, notes_dir, hypotheses_dir),
    )
    state.alarm_keys = classify_alarms(
        state,
        qpr_critical=qpr_critical,
        cmr_hot=cmr_hot,
        hcr_redirect=hcr_redirect,
        swr_archive=swr_archive,
    )
    return state


# ---------------------------------------------------------------------------
# CLI entrypoint (for /stats skill)
# ---------------------------------------------------------------------------


def main() -> None:
    """Print metabolic state as JSON for a given vault path."""
    import sys

    if len(sys.argv) < 2:
        msg = "Usage: python -m engram_r.metabolic_indicators <vault>"
        print(json.dumps({"error": msg}))
        sys.exit(1)

    vault_path = Path(sys.argv[1])
    if not vault_path.is_dir():
        print(json.dumps({"error": f"Not a directory: {vault_path}"}))
        sys.exit(1)

    state = compute_metabolic_state(vault_path)
    print(
        json.dumps(
            {
                "qpr": round(state.qpr, 1),
                "vdr": round(state.vdr, 1),
                "cmr": round(state.cmr, 1),
                "hcr": round(state.hcr, 1),
                "swr": round(state.swr, 1),
                "alarm_keys": state.alarm_keys,
            }
        )
    )


if __name__ == "__main__":
    main()
