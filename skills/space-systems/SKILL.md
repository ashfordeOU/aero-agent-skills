---
name: space-systems
description: "Use when a task concerns space systems engineering for European space projects: guide the router to the space-systems pack, whose ECSS software-engineering sub-skill covers space software criticality (A-D), assurance and verification rigor, lifecycle gates, and heritage-reuse evidence. This pack is the space counterpart of the avionics certification spine and follows the ECSS series as the European space procurement baseline. Trigger: space systems, space software, spacecraft software, ECSS, E-ST-40C, Q-ST-80C, space flight software, heritage software."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; router/entry point for the space-systems domain pack"
metadata:
  domain: space-systems
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Space systems domain pack (router)

Route here when the task is space systems engineering, especially
spacecraft software, under the ECSS series.

## Domain

Space systems and astrodynamics: spacecraft subsystem engineering and
European space software assurance (ECSS-E-ST-40C software engineering,
Q-ST-80C product assurance).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| space-systems/ecss/software-engineering | ECSS space software | criticality A-D, lifecycle gates, heritage reuse |

## Routing guidance

- Space software questions (criticality classification, assurance rigor,
  lifecycle reviews, heritage reuse) route to the ECSS sub-skill.
- Aircraft software and hardware questions route to the avionics pack.
- System-level engineering and safety questions route to the
  systems-engineering-safety pack.

## Install

To install only this pack, copy or symlink the leaf folder above into
your host's skills directory (see README Install for per-host commands).
