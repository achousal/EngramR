---
description: "When all daemon tasks are marked done, the loop must escalate to idle cooldown rather than re-evaluating at task cooldown interval every 2 minutes"
type: methodology
category: behavior
source: "session-mining"
session_source: "ops/daemon/logs/daemon-20260223-004120.log"
created: "2026-02-23"
status: active
---

# daemon requires consecutive-skip idle fallback to prevent tight polling loops

## What to Do

When implementing or modifying the daemon scheduler, ensure that consecutive task skips trigger an escalation to idle cooldown. The fix introduced in `fix(daemon): add consecutive-skip idle fallback in daemon.sh` (commit a702f2e) establishes the correct pattern:

- Track a consecutive-skip counter that increments each loop iteration where all tasks are skipped (markers exist, priorities not met, or no eligible tasks)
- After 3 consecutive skips, switch from the task cooldown interval (2 minutes) to the idle cooldown interval (30 minutes)
- Reset the counter to zero whenever any task actually executes

The scheduler-side complement (marker awareness) belongs in `daemon_scheduler.py`; the bash-side complement (consecutive-skip counter) belongs in `daemon.sh`. Both layers are needed.

## What to Avoid

Do not rely solely on individual task marker checks to determine idle state. When all P1-P4 tasks have completion markers, the scheduler correctly returns "skip" for each task, but without an idle fallback, the daemon enters a tight loop: health gate check every 2 minutes, SKIP, 2-minute cooldown, repeat. This consumed 7+ hours of compute from 01:20 to 09:00 on 2026-02-23 with no work performed.

Do not remove the consecutive-skip counter without replacing it with an equivalent idle detection mechanism.

## Why This Matters

Without the idle fallback, a fully-caught-up daemon runs the health gate (~1 API call) and scheduler (~1 API call) every 2 minutes indefinitely. At 30 minutes of API calls per hour, this exhausts rate limits, generates unnecessary cost, and fills the log with noise that obscures real events. The vault ran ~360 SKIP iterations over 7 hours before the fix was applied.

The correct behavior: after all work is done, sleep for 30 minutes before checking again. New sessions, new vault state, or timer-based triggers will wake the daemon at the appropriate time.

## Scope

Applies to all modifications to `ops/scripts/daemon.sh` and `_code/src/engram_r/daemon_scheduler.py`. When testing daemon changes locally, always verify behavior after a full task completion cycle -- the idle state is the hardest state to test but the most important for long-running stability.

---

Related: [[methodology]]
