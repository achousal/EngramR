---
engine_version: "0.8.0"
research_snapshot: "2026-02-21"
generated_at: "2026-02-21T21:45:00Z"
platform: claude-code
kernel_version: "1.0"

dimensions:
  granularity: atomic
  organization: flat
  linking: explicit+implicit
  processing: heavy
  navigation: 3-tier
  maintenance: condition-based
  schema: moderate
  automation: full

active_blocks:
  - wiki-links
  - atomic-notes
  - mocs
  - processing-pipeline
  - schema
  - maintenance
  - self-evolution
  - methodology-knowledge
  - session-rhythm
  - templates
  - ethical-guardrails
  - helper-functions
  - graph-analysis
  - semantic-search
  - self-space

coherence_result: passed

vocabulary:
  notes: "notes"
  inbox: "inbox"
  archive: "archive"
  ops: "ops"

  note: "claim"
  note_plural: "claims"

  description: "description"
  topics: "topics"
  relevant_notes: "relevant claims"

  topic_map: "topic map"
  hub: "hub"

  reduce: "reduce"
  reflect: "reflect"
  reweave: "reweave"
  verify: "verify"
  validate: "validate"
  rethink: "rethink"

  cmd_reduce: "/reduce"
  cmd_reflect: "/reflect"
  cmd_reweave: "/reweave"
  cmd_verify: "/verify"
  cmd_rethink: "/rethink"

  extraction_categories:
    - name: "claims"
      what_to_find: "Testable assertions about mechanisms, effects, or relationships"
      output_type: "claim"
    - name: "evidence"
      what_to_find: "Data points, measurements, statistical results"
      output_type: "claim"
    - name: "methodology-comparisons"
      what_to_find: "How different studies approached similar questions"
      output_type: "claim"
    - name: "contradictions"
      what_to_find: "Results or interpretations that conflict with existing claims"
      output_type: "claim"
    - name: "open-questions"
      what_to_find: "Gaps in evidence, unresolved mechanisms, future directions"
      output_type: "claim"
    - name: "design-patterns"
      what_to_find: "Reusable experimental designs, analytical approaches"
      output_type: "claim"

platform_hints:
  context: fork
  allowed_tools:
    - Read
    - Write
    - Edit
    - Glob
    - Grep
    - Bash
    - Task
  semantic_search_tool: qmd

personality:
  warmth: clinical
  opinionatedness: neutral
  formality: formal
  emotional_awareness: task-focused
---
