---
name: avionics
description: "Use when a task concerns avionics and flight software assurance for civil aircraft: guide the router to the avionics pack, whose DO-178C software lifecycle sub-skills cover planning, development, verification, and configuration management, whose DO-254 sub-skills cover airborne electronic hardware planning and verification, whose DO-330 tool-qualification sub-skill covers software tool credit, whose DO-160 environmental-qualification sub-skill covers equipment test conditions, and whose far-cs25 airworthiness sub-skill covers the transport-category certification basis. This pack is the airborne software and hardware certification spine. Trigger: avionics, airborne software, flight software, DO-178C, DO-254, DO-330, DO-160, airborne electronic hardware, airworthiness certification, software levels, tool qualification, environmental qualification."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
  - id: do-254
    reference-only: true
  - id: do-330
    reference-only: true
  - id: do-160
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
certification (DO-178C), software tool qualification (DO-330),
airborne electronic hardware design assurance (DO-254),
environmental qualification (DO-160), and transport-category
airworthiness certification (FAR-25/CS-25).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| avionics/do178c/planning | DO-178C planning | software level/DAL, PSAC, planning artifacts |
| avionics/do178c/development | DO-178C development | requirement-to-code traceability, derived requirements |
| avionics/do178c/verification | DO-178C verification | structural coverage, MC/DC, independence |
| avionics/do178c/software-testing | DO-178C software testing | requirements-based test case generation, MC/DC test case count, coverage objectives per level |
| avionics/do178c/configuration-management | DO-178C configuration management | baselines, problem reports, release gate |
| avionics/do178c/tool-qualification | DO-330 tool qualification | TQL per tool criterion, tool credit, TOR |
| avionics/do178c/airworthiness-liaison | DO-178C airworthiness liaison | certification basis coverage, SOI audits, open items |
| avionics/do160/environmental-qualification | DO-160 environmental qualification | test matrix per equipment category, temperature/vibration/EMC |
| avionics/do160/lightning-protection | DO-160 lightning protection | section 22 induced transients, lightning protection zones |
| avionics/do160/electrostatic-discharge | DO-160 electrostatic discharge | section 25 ESD air discharge level, 150 pF / 330 ohm generator model, test point applicability |
| avionics/do160/radio-frequency-susceptibility | DO-160 RF susceptibility | RS103 radiated immunity, CS114 conducted immunity, field strength |
| avionics/do160/power-input | DO-160 power input | section 16 voltage limits, sag/surge transients, frequency tolerance |
| avionics/do254/hardware-planning | DO-254 hardware planning | simple vs complex AEH, PHAC |
| avionics/do254/verification | DO-254 verification | verification methods per AEH class, independence, coverage |
| avionics/do254/configuration-management | DO-254 configuration management | baselines, ECR/ECO, change class, hardware configuration index |
| avionics/do254/requirements-capture | DO-254 requirements capture | requirement characteristics, derived requirements, trace links |
| avionics/far-cs25/airworthiness | FAR-25/CS-25 airworthiness | certification basis, means of compliance, 25.1309 |
| avionics/far-cs25/special-conditions | FAR-25/CS-25 special conditions | novel design features, FAR 25.17, special-condition scope |
| avionics/flight-management/flight-planning | FMS flight planning | great-circle track distance, waypoints, leg geometry |
| avionics/flight-management/vertical-navigation | FMS vertical navigation | top of descent, descent gradient, altitude constraints, VNAV path |
| avionics/data-bus/arinc429-protocol | ARINC 429 protocol | ARINC 429 word format, octal label, SDI, BNR, BCD, SSM, odd parity, 12.5 or 100 kbps, transmitter receiver topology |

## Routing guidance

- Software certification questions (levels, PSAC, coverage, traceability,
  baselines) route to the DO-178C sub-skills.
- Requirements-based test case generation and structural coverage
  measurement questions (MC/DC test case count, coverage objectives per
  level) route to the DO-178C software-testing sub-skill; verification
  process questions (reviews, analyses, independence) stay with the
  verification sub-skill.
- Tool credit and qualification questions route to the DO-330 sub-skill.
- Environmental test questions (temperature, vibration, EMC, lightning,
  RF immunity) route to the DO-160 sub-skills.
- Electrostatic discharge questions (section 25 air discharge level,
  150 pF / 330 ohm generator model, discharge counts, test point
  applicability from personnel accessibility) route to the DO-160
  electrostatic-discharge sub-skill, not to lightning-protection or
  power-input.
- Power-input questions (section 16 voltage limits, sag/surge transients,
  frequency tolerance, emergency power) route to the DO-160 power-input
  sub-skill.
- Hardware assurance questions (AEH classification, PHAC, verification,
  requirements capture) route to the DO-254 sub-skills.
- Hardware configuration and change-control questions (baselines,
  ECR/ECO, HCI) route to the DO-254 configuration-management sub-skill.
- Type-certification basis questions (FAR-25 vs CS-25, 25.1309) route to
  the far-cs25 airworthiness sub-skill.
- Novel-feature questions (special conditions, FAR 25.17, equivalent
  safety) route to the far-cs25 special-conditions sub-skill.
- FMS route questions (waypoints, leg geometry, TOD, VNAV constraints)
  route to the flight-management sub-skills.
- ARINC 429 word encoding and decoding, octal label, SDI, BNR and BCD
  data fields, SSM, and odd parity questions route to the data-bus
  arinc429-protocol sub-skill.
- System-level engineering and safety questions route to the
  systems-engineering-safety pack instead.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
