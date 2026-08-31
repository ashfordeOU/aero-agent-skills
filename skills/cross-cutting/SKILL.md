---
name: cross-cutting
description: "Use when a task concerns the skill delivery and packaging layer rather than aerospace engineering content: guide the router to the cross-cutting pack, whose SEP-2640 skill-delivery sub-skill covers SKILL.md conformance, skill URIs, and MCP resources behind the directoryRead capability. This pack is the library's own meta-layer for distributing skills to agent hosts. Trigger: skill delivery, skill packaging, SEP-2640, skills over MCP, skill URI, MCP resources, directory read, agentskills.io."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: sep-2640
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; router/entry point for the cross-cutting domain pack"
metadata:
  domain: cross-cutting
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Cross-cutting domain pack (router)

Route here when the task is the skill format, packaging, or delivery
layer rather than aerospace engineering content.

## Domain

Cross-cutting and foundational: the skill-format and delivery
specification (SEP-2640) that governs how this library packages and
serves skills over MCP.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| cross-cutting/sep2640/skill-delivery | SEP-2640 skill delivery | SKILL.md packaging, skill URIs, MCP resources, server readiness |

## Routing guidance

- Skill packaging and MCP delivery questions route to the SEP-2640
  sub-skill.
- Aerospace engineering questions route to their domain pack
  (avionics, space-systems, systems-engineering-safety,
  manufacturing-quality).

## Install

To install only this pack, copy or symlink the leaf folder above into
your host's skills directory (see README Install for per-host commands).
