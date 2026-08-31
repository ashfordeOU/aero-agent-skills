---
name: systems-engineering-safety
description: "Use when a task concerns aircraft or system-level engineering and safety assurance: guide the router to the systems-engineering-safety pack, covering ARP4754A systems planning and FDAL/IDAL allocation, the ARP4761A safety assessment process (FHA/PSSA/SSA and the FTA/FMEA/CCA analysis set), and model-based systems engineering with SysML and digital-thread traceability. This pack is the systems-level spine above item-level software and hardware assurance. Trigger: systems engineering, systems safety, ARP4754A, ARP4761A, safety assessment, MBSE, SysML, FDAL, IDAL, FHA, PSSA, SSA, FMEA."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; router/entry point for the systems-engineering-safety domain pack"
metadata:
  domain: systems-engineering-safety
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Systems engineering and safety domain pack (router)

Route here when the task is aircraft or system-level engineering,
safety assessment, or model-based systems engineering.

## Domain

Systems engineering and safety: development planning and development
assurance (ARP4754A), the safety assessment process (ARP4761A), and
model-based systems engineering (SysML, digital thread).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| systems-engineering-safety/arp4754a/systems-planning | ARP4754A systems planning | FDAL/IDAL allocation, certification and development plans |
| systems-engineering-safety/arp4761a/safety-assessment | ARP4761A safety assessment | FHA/PSSA/SSA sequence, analysis set selection |
| systems-engineering-safety/mbse/systems-engineering | MBSE systems engineering | SysML modeling, function allocation, traceability closure |

## Routing guidance

- Development assurance and planning questions route to the ARP4754A
  sub-skill.
- Safety assessment questions (severity, FHA/PSSA/SSA, FTA/FMEA/CCA)
  route to the ARP4761A sub-skill.
- Modeling and digital-thread questions route to the MBSE sub-skill.
- Item-level software or hardware questions route to the avionics pack.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
