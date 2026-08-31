---
name: avionics
description: "Use when a task concerns avionics and flight software assurance for civil aircraft: guide the router to the avionics pack, whose DO-178C software lifecycle sub-skills cover planning, development, verification, and configuration management, the DO-254 hardware-planning sub-skill covers airborne electronic hardware, and the far-cs25 airworthiness sub-skill covers the transport-category certification basis. This pack is the airborne software and hardware certification spine. Trigger: avionics, airborne software, flight software, DO-178C, DO-254, airborne electronic hardware, airworthiness certification, software levels."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
  - id: do-254
    reference-only: true
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; router/entry point for the avionics domain pack"
metadata:
  domain: avionics
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Avionics domain pack (router)

Route here when the task is avionics and flight software assurance for
civil aircraft. This pack is the certification spine for airborne
software and hardware.

## Domain

Avionics and flight software assurance: airborne software lifecycle
certification (DO-178C), airborne electronic hardware design assurance
(DO-254), and transport-category airworthiness certification
(FAR-25/CS-25).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| avionics/do178c/planning | DO-178C planning | software level/DAL, PSAC, planning artifacts |
| avionics/do178c/development | DO-178C development | requirement-to-code traceability, derived requirements |
| avionics/do178c/verification | DO-178C verification | structural coverage, MC/DC, independence |
| avionics/do178c/configuration-management | DO-178C configuration management | baselines, problem reports, release gate |
| avionics/do254/hardware-planning | DO-254 hardware planning | simple vs complex AEH, PHAC |
| avionics/far-cs25/airworthiness | FAR-25/CS-25 airworthiness | certification basis, means of compliance, 25.1309 |

## Routing guidance

- Software certification questions (levels, PSAC, coverage, traceability,
  baselines) route to the DO-178C sub-skills.
- Hardware assurance questions (AEH classification, PHAC) route to the
  DO-254 sub-skill.
- Type-certification basis questions (FAR-25 vs CS-25, 25.1309) route to
  the far-cs25 sub-skill.
- System-level engineering and safety questions route to the
  systems-engineering-safety pack instead.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
