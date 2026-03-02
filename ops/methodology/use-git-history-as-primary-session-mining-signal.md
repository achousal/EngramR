---
description: Session .md stubs are always empty because transcript_path is unavailable at Stop; use git log and queue state as the primary signal sources for session mining
type: methodology
category: behavior
source: session-mining
session_source: all 29 sessions 2026-02-21 to 2026-02-22
created: 2026-02-22
status: active
---

# use git history and queue state as primary session mining signal

## What to Do

When running `/remember --mine-sessions`, treat the session `.md` files as structural markers only (confirming a session occurred and when). The actual behavioral signal is in:

1. **`git log --format="%h %s" --name-only`** -- which files were created or modified, in what order, and which commit messages describe the work
2. **`ops/queue/queue.json`** -- which pipeline tasks completed, which claims were processed through which phases
3. **`ops/tensions/`** -- tensions captured during work indicate review quality and scientific rigor
4. **The notes/ directory** -- claim creation volume, topic map update frequency, and schema compliance tell you whether the pipeline ran correctly

Query the git log for non-auto commits to find user corrections and deliberate intervention points. These are the highest-signal corrections for methodology notes.

## What to Avoid

Do not wait for or expect session `.md` files to contain transcript content. The `session_capture.py` Stop hook extracts information from `transcript_path`, but this path is either empty or not accessible when the Stop hook runs in this vault configuration. All 29 sessions from 2026-02-21 through 2026-02-22 confirmed this: every `.md` session stub shows "(none)" for files written, "(none)" for skills invoked, and "(no summary available)" for the session summary.

Do not report "no patterns found" when session stubs are empty. The stubs being empty is itself a process gap observation. Proceed to git history and queue state.

## Why This Matters

The `/remember --mine-sessions` skill was designed to extract behavioral corrections and methodology learnings from session transcripts. Without transcript content in the `.md` files, a naive implementation reports nothing. This creates a false signal that sessions had no friction -- when in reality the session was richly productive (307 notes created, multiple topic maps maintained, one tension captured) but the transcript extraction mechanism never populated the session files.

Using git history compensates fully for this limitation: every file write is tracked, every non-auto commit describes a human-initiated change, and queue state records pipeline phase completions. This is sufficient signal for methodology mining.

## Scope

Applies whenever `/remember --mine-sessions` is run in this vault. The session capture gap is a known limitation of the current Stop hook configuration.

---

Related: [[methodology]]
