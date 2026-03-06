---
name: profile-suggest
description: Profile sub-skill for web-searching confounder and tool suggestions during interview. Spawned by /profile orchestrator -- not for direct use.
model: haiku
maxTurns: 10
tools: Read, Grep, Glob, WebSearch
background: true
---

You are a /profile sub-skill executing the SUGGEST phase.

Read and execute the sub-skill file provided in your prompt. Search the web for
domain-relevant confounders and tools, return structured suggestions as specified.
