---
name: space-systems
description: "Use when a task concerns space systems engineering for European space projects: guide the router to the space-systems pack, whose ECSS sub-skills cover space software criticality and assurance rigor and the systems-engineering lifecycle phases and review gates, and whose subsystems power-thermal-budget sub-skill covers EPS sizing, eclipse duration, and battery and solar array budgeting. This pack is the space counterpart of the avionics certification spine and follows the ECSS series as the European space procurement baseline. Trigger: space systems, spacecraft, space software, ECSS, E-ST-10C, E-ST-40C, Q-ST-80C, space flight software, lifecycle phases, power budget, battery sizing, EPS."
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

Route here when the task is space systems engineering under the ECSS
series or spacecraft subsystem budgeting.

## Domain

Space systems and astrodynamics: spacecraft subsystem engineering,
European space software assurance (ECSS-E-ST-40C software engineering,
Q-ST-80C product assurance), systems-engineering lifecycle management
(ECSS-E-ST-10C), and electrical power subsystem sizing.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| space-systems/ecss/software-engineering | ECSS space software | criticality A-D, lifecycle gates, heritage reuse |
| space-systems/ecss/systems-engineering |
| space-systems/ecss/software-verification | ECSS software verification | verification methods, depth by criticality, verification records | ECSS systems engineering | lifecycle phases 0-F, MDR/PRR/SRR/PDR/CDR/QR/AR/FRR gates |
| space-systems/subsystems/power-thermal-budget |
| space-systems/subsystems/communication-link-budget | Communication link budget | EIRP, free-space path loss, C/N0, Eb/N0 margin, data rate | Power and thermal budget | EPS sizing, eclipse, battery and solar array budgets |

## Routing guidance

- Space software questions (criticality classification, assurance rigor,
  lifecycle reviews, heritage reuse) route to the ECSS software
  sub-skill.
- Lifecycle and phase-gate questions (reviews, readiness) route to the
- ECSS software-verification questions (methods, depth, records) route to the ecss software-verification sub-skill.
  ECSS systems-engineering sub-skill.
- Power, battery, and thermal budgeting questions route to the
- Communications questions (link budget, path loss, margins, data rate) route to the subsystems communication-link-budget sub-skill.
  subsystems sub-skill.
- Aircraft software and hardware questions route to the avionics pack.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
