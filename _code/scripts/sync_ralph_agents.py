#!/usr/bin/env python3
"""Generate .claude/agents/ralph-*.md files from ops/daemon-config.yaml.

Keeps interactive (named subagent) and daemon (CLI --model) model routing in sync.
Run after editing daemon-config.yaml to propagate model/maxTurns changes to agent
frontmatter.

Usage:
    python _code/scripts/sync_ralph_agents.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parents[2]
AGENTS_DIR = VAULT / ".claude" / "agents"
DAEMON_CONFIG = VAULT / "ops" / "daemon-config.yaml"

# Phase definitions: name -> (daemon-config model key, daemon-config max_turns key,
#                              tools, skills, description, body)
RALPH_PHASES: dict[str, dict] = {
    "ralph-extract": {
        "model_key": "reduce",
        "turns_key": "extract",
        "tools": "Read, Write, Edit, Grep, Glob, Bash",
        "skills": ["reduce"],
        "description": (
            "Ralph pipeline worker for the extract (reduce) phase. "
            "Extracts structured claims from source material. "
            "Spawned by /ralph orchestrator -- not for direct use."
        ),
        "body": (
            "You are a ralph pipeline worker executing the EXTRACT phase "
            "for a source document.\n\n"
            "You receive a prompt from the ralph orchestrator containing:\n"
            "- The task file path and task identity\n"
            "- The source file to extract from\n"
            "- Instructions to run /reduce --handoff\n\n"
            "Execute ONE phase only. Extract all domain-relevant claims from the source.\n"
            "Create per-claim task files and update the queue with new entries.\n\n"
            "When complete, output a RALPH HANDOFF block with:\n"
            "- Work Done: number of claims extracted, list of task files created\n"
            "- Learnings: any friction, surprises, or methodology insights (or NONE)\n"
            "- Queue Updates: new task entries added to queue"
        ),
    },
    "ralph-create": {
        "model_key": "create",
        "turns_key": "create",
        "tools": "Read, Write, Grep, Glob",
        "skills": [],
        "description": (
            "Ralph pipeline worker for the create phase. "
            "Creates a single claim note from a task file. "
            "Spawned by /ralph orchestrator -- not for direct use."
        ),
        "body": (
            "You are a ralph pipeline worker executing the CREATE phase "
            "for a single claim.\n\n"
            "You receive a prompt from the ralph orchestrator containing:\n"
            "- The task file path and task identity\n"
            "- The target claim title\n"
            "- Instructions for note structure (YAML frontmatter, body, footer)\n\n"
            "Create exactly one claim note in notes/. Follow these rules:\n"
            "- YAML frontmatter with description (adds info beyond title)\n"
            "- CRITICAL: ALL YAML string values MUST be wrapped in double quotes\n"
            "- Body: 150-400 words showing reasoning with connective words\n"
            "- Footer: Source (wiki link), Relevant Notes (with context), Topics\n"
            "- Update the task file's ## Create section\n\n"
            "Execute ONE phase only. Do NOT run reflect or any subsequent phase.\n\n"
            "When complete, output a RALPH HANDOFF block with:\n"
            "- Work Done: the claim title and file path created\n"
            "- Learnings: any friction, surprises, or methodology insights (or NONE)\n"
            "- Queue Updates: confirmation that create phase is complete for this task"
        ),
    },
    "ralph-enrich": {
        "model_key": "enrich",
        "turns_key": "enrich",
        "tools": "Read, Write, Edit, Grep, Glob",
        "skills": ["enrich"],
        "description": (
            "Ralph pipeline worker for the enrich phase. "
            "Integrates new evidence into an existing claim. "
            "Spawned by /ralph orchestrator -- not for direct use."
        ),
        "body": (
            "You are a ralph pipeline worker executing the ENRICH phase "
            "for a single claim.\n\n"
            "You receive a prompt from the ralph orchestrator containing:\n"
            "- The task file path and task identity\n"
            "- The target claim to enrich\n"
            "- Instructions to run /enrich --handoff\n\n"
            "Execute ONE phase only. Do NOT run reflect or any subsequent phase.\n\n"
            "When complete, output a RALPH HANDOFF block with:\n"
            "- Work Done: what evidence was added and how the claim was updated\n"
            "- Learnings: any friction, surprises, or methodology insights (or NONE)\n"
            "- Queue Updates: confirmation that enrich phase is complete for this task"
        ),
    },
    "ralph-reflect": {
        "model_key": "reflect",
        "turns_key": "reflect",
        "tools": "Read, Write, Edit, Grep, Glob",
        "skills": ["reflect"],
        "description": (
            "Ralph pipeline worker for the reflect phase. "
            "Finds connections between a claim and the existing knowledge graph, "
            "updates topic maps. "
            "Spawned by /ralph orchestrator -- not for direct use."
        ),
        "body": (
            "You are a ralph pipeline worker executing the REFLECT phase "
            "for a single claim.\n\n"
            "You receive a prompt from the ralph orchestrator containing:\n"
            "- The task file path and task identity\n"
            "- The target claim to reflect on\n"
            "- Sibling claims from the same batch (check connections to these)\n"
            "- Instructions to run /reflect --handoff\n\n"
            "Execute ONE phase only. Do NOT run reweave or any subsequent phase.\n\n"
            "When complete, output a RALPH HANDOFF block with:\n"
            "- Work Done: what connections you found and which topic maps you updated\n"
            "- Learnings: any friction, surprises, or methodology insights (or NONE)\n"
            "- Queue Updates: confirmation that reflect phase is complete for this task"
        ),
    },
    "ralph-reweave": {
        "model_key": "reweave",
        "turns_key": "reweave",
        "tools": "Read, Write, Edit, Grep, Glob",
        "skills": ["reweave"],
        "description": (
            "Ralph pipeline worker for the reweave phase. "
            "Updates older notes with backward connections to a newer claim. "
            "Spawned by /ralph orchestrator -- not for direct use."
        ),
        "body": (
            "You are a ralph pipeline worker executing the REWEAVE phase "
            "for a single claim.\n\n"
            "You receive a prompt from the ralph orchestrator containing:\n"
            "- The task file path and task identity\n"
            "- The target claim to reweave\n"
            "- Sibling claims from the same batch\n"
            "- Instructions to run /reweave --handoff\n\n"
            "This is the BACKWARD pass. Find OLDER claims AND sibling claims that should\n"
            "reference this claim but don't. Add inline links FROM older claims TO this claim.\n\n"
            "Execute ONE phase only. Do NOT run verify or any subsequent phase.\n\n"
            "When complete, output a RALPH HANDOFF block with:\n"
            "- Work Done: which older notes were updated with backward links\n"
            "- Learnings: any friction, surprises, or methodology insights (or NONE)\n"
            "- Queue Updates: confirmation that reweave phase is complete for this task"
        ),
    },
    "ralph-verify": {
        "model_key": "verify",
        "turns_key": "verify",
        "tools": "Read, Write, Edit, Grep, Glob",
        "skills": ["verify"],
        "description": (
            "Ralph pipeline worker for the verify phase. "
            "Runs recite + validate + review quality checks on a single claim. "
            "Spawned by /ralph orchestrator -- not for direct use."
        ),
        "body": (
            "You are a ralph pipeline worker executing the VERIFY phase "
            "for a single claim.\n\n"
            "You receive a prompt from the ralph orchestrator containing:\n"
            "- The task file path and task identity\n"
            "- The target claim to verify\n"
            "- Instructions to run /verify --handoff\n\n"
            "Execute the combined verification:\n"
            "1. RECITE: Read only title + description, predict what the body should contain, "
            "THEN read the full claim\n"
            "2. VALIDATE: Check schema compliance (YAML frontmatter, required fields, enum values)\n"
            "3. REVIEW: Per-note health (description quality, link health, content quality)\n\n"
            "Execute ONE phase only. This is the final phase for this claim.\n\n"
            "When complete, output a RALPH HANDOFF block with:\n"
            "- Work Done: verification results (pass/warn/fail per check)\n"
            "- Learnings: any friction, surprises, or methodology insights (or NONE)\n"
            "- Queue Updates: confirmation that verify phase is complete for this task"
        ),
    },
    "ralph-cross-connect": {
        "model_key": "cross_connect",
        "turns_key": "cross_connect",
        "tools": "Read, Write, Edit, Grep, Glob",
        "skills": [],
        "description": (
            "Ralph pipeline worker for post-batch cross-connect validation. "
            "Verifies sibling links between batch claims and adds any that were missed. "
            "Spawned by /ralph orchestrator -- not for direct use."
        ),
        "body": (
            "You are a ralph pipeline worker executing POST-BATCH CROSS-CONNECT validation.\n\n"
            "You receive a prompt from the ralph orchestrator containing:\n"
            "- The batch identifier\n"
            "- A list of all note titles and paths created in this batch\n\n"
            "Verify sibling connections exist between batch notes. Add any connections that\n"
            "were missed because sibling notes did not exist yet when an earlier claim's\n"
            "reflect phase ran. Check backward link gaps.\n\n"
            "When complete, output a RALPH HANDOFF block with:\n"
            "- Work Done: sibling connections validated, missing connections added\n"
            "- Learnings: any friction, surprises, or methodology insights (or NONE)\n"
            "- Queue Updates: cross-connect validation complete for this batch"
        ),
    },
}

# Model name normalization: daemon-config uses short names (opus/sonnet/haiku)
# Agent frontmatter also uses short names, so no conversion needed.


def load_daemon_config() -> dict:
    """Load and return daemon-config.yaml."""
    if not DAEMON_CONFIG.exists():
        print(f"WARNING: {DAEMON_CONFIG} not found, using defaults", file=sys.stderr)
        return {}
    with open(DAEMON_CONFIG) as f:
        return yaml.safe_load(f) or {}


def render_agent(name: str, phase: dict, models: dict, max_turns: dict) -> str:
    """Render a single agent markdown file."""
    model = models.get(phase["model_key"], "sonnet")
    turns = max_turns.get(phase["turns_key"], 15)

    lines = ["---"]
    lines.append(f"name: {name}")
    lines.append(f"description: {phase['description']}")
    lines.append(f"model: {model}")
    lines.append(f"maxTurns: {turns}")
    lines.append(f"tools: {phase['tools']}")
    if phase["skills"]:
        lines.append("skills:")
        for skill in phase["skills"]:
            lines.append(f"  - {skill}")
    lines.append("---")
    lines.append("")
    lines.append(phase["body"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    args = parser.parse_args()

    config = load_daemon_config()
    models = config.get("models", {})
    max_turns = config.get("max_turns", {})

    changed = 0
    for name, phase in RALPH_PHASES.items():
        content = render_agent(name, phase, models, max_turns)
        path = AGENTS_DIR / f"{name}.md"

        if args.dry_run:
            existing = path.read_text() if path.exists() else ""
            status = "unchanged" if existing == content else "CHANGED"
            print(f"  {name}: {status} (model={models.get(phase['model_key'], 'sonnet')}, "
                  f"maxTurns={max_turns.get(phase['turns_key'], 15)})")
            continue

        existing = path.read_text() if path.exists() else ""
        if existing != content:
            path.write_text(content)
            changed += 1
            print(f"  Updated: {name}.md")
        else:
            print(f"  Unchanged: {name}.md")

    if not args.dry_run:
        print(f"\nSync complete: {changed} file(s) updated out of {len(RALPH_PHASES)}")
    else:
        print(f"\nDry run: {len(RALPH_PHASES)} agent(s) checked")


if __name__ == "__main__":
    main()
