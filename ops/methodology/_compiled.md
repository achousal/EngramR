# Methodology Directives (compiled)

Auto-loaded at session start. Source notes in ops/methodology/.
Regenerate when source notes change significantly.

## Mechanical Guards (hook-enforced)

These are enforced by validate_write and sanitize_title hooks. Listed for awareness only:

- **Slash in titles** -- `/` in claim titles creates subdirectories. Use `-` instead (APP-PS1, APOE3-3). Hook blocks nested writes to notes/.
- **Unicode normalization** -- Queue IDs and filenames must use NFC UTF-8, not JSON-escaped sequences. Use `ensure_ascii=False` in json.dump.
- **YAML quoting** -- Commit messages in source/session_source fields contain colons that break YAML. Always double-quote string values in raw frontmatter. note_builder yaml.dump handles this automatically.
- **Pipeline provenance** -- notes/ files must have a non-empty `description:` field (blocked by hook). New claim-type notes (Write tool) warn if missing `source:` field. MOCs exempt from source check. Controlled by `pipeline_compliance: true` in ops/config.yaml.

## Behavioral Rules

**Parallel workflow integrity** -- Reduce can fan out (each source independent). Reflect must fan in (needs full graph). Never parallelize /reflect, /reweave, or /tournament. Queue (queue.json) is single-writer; use /ralph as coordinator. After parallel work: /health, /graph orphans, /reflect.

**Health reports are diagnostic artifacts** -- ops/health/ and ops/queue/ files contain wiki-link syntax for readability but are NOT graph nodes. Never scan these directories for dangling links. The canonical link checker (dangling-links.sh) is scoped to notes/, _research/, self/, projects/ only.

**Session mining uses git history** -- Session .md stubs are always empty (transcript_path unavailable at Stop hook). Use `git log --name-only` for non-auto commits, queue.json for phase completions, and notes/ for creation volume. Do not report "no patterns found" when session stubs are empty.

**Symlinked repos need wiki-link bridges** -- Symlinked _dev/ repos are Obsidian-indexed but internal docs are graph orphans without explicit links. Every symlinked project note needs a `## Key Docs` section with context phrases linking to significant internal .md files.

**Daemon idle fallback** -- When all daemon tasks are skipped, a consecutive-skip counter must escalate from 2-minute task cooldown to 30-minute idle cooldown after 3 consecutive skips. Without this, the daemon tight-loops health checks indefinitely. Counter resets when any task executes.

**Cross-repo experiment sync** -- When an experiment completes in a lab directory (_dev/), update the vault: hypothesis frontmatter (status, outcome), execution tracker (step status), research goal (empirical findings), and copy key results into experiment note body.

## Experiment Conventions

- **Step-based naming**: `step{NN}_{description}.{ext}` -- never paper-style (fig01, tableS1)
- **Required artifacts**: `README.md` (file manifest) + `execution_log.yaml` (structured timeline) in every results directory
- **Data provenance**: SHA256 checksum of raw data in `run_metadata.txt`

## Configuration Rationale

Vault uses atomic granularity, flat organization, heavy processing, 3-tier navigation (hub > domain > claim), full automation. High-risk failure modes: Collector's Fallacy, Orphan Drift, Verbatim Risk, MOC Sprawl, Productivity Porn.
