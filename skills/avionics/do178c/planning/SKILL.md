---
name: planning
description: "Use when planning DO-178C software certification for airborne systems or equipment: determine the software level or DAL (A-E) from failure-condition severity, draft the PSAC (Plan for Software Aspects of Certification), and scope planning-phase artifacts such as the PSAC, SDP, SVP, SCM, and SQA plans. Covers ARP4754A FDAL/IDAL allocation and ARP4761A severity-to-DAL propagation, including coverage-depth implications per level: A requires MC/DC, B requires decision coverage, C requires statement coverage, D and E require none. Trigger: DO-178C planning, PSAC, software level determination, DAL assignment, development assurance, certification planning, ARP4754A, ARP4761A, airborne software certification."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: DO-178C
    reference-only: true
  - id: ARP4754A
    reference-only: true
  - id: ARP4761A
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do178c
  tags: [do-178c, dal, psac, certification, arp4754a, arp4761a, software-levels]
  version: 0.1.0
  author: AeroSkills
---

# DO-178C Planning (avionics/do178c/planning)

Use when the task is DO-178C planning-phase work: drafting a PSAC,
determining the software level (DAL) for a function or item, or scoping
planning-phase artifacts (PSAC, SDP, SVP, SCM, SQA plans).

## Domain quick reference

- Software levels (DO-178C): A = Catastrophic, B = Hazardous, C = Major,
  D = Minor, E = No safety effect.
- ARP4754A splits development assurance: FDAL (function) vs IDAL (item);
  an item's IDAL is the highest FDAL among the functions it implements.
- ARP4761A propagates failure-condition severity to DAL.
- Coverage depth scales with DAL: A = 100% MC/DC, B = 100% decision,
  C = 100% statement, D/E = none required.
- Accepted means of compliance: AC 20-115D (software), AC 20-174 (ARP4754A).

## Workflow

1. Confirm certification basis and applicable standards.
2. Determine failure-condition severity per ARP4761A (FHA/PSSA inputs).
3. Allocate DAL / FDAL / IDAL per ARP4754A + ARP4761A.
4. Map DAL to DO-178C software level and objectives tables.
5. Draft PSAC and planning-phase artifacts.

## Pitfalls

- DAL from severity alone without FDAL/IDAL split.
- Coverage depth mismatched to level (A requires MC/DC, not statement).
- Traceability gaps (no derived requirements).

## Behavior contract (gate 3)

This skill ships its own contract test, like every skill in the library:
scripts/test_do178c_levels.py against scripts/do178c_levels.py (stdlib
unittest, offline). Run: python3
skills/avionics/do178c/planning/scripts/test_do178c_levels.py

## Compliance

- Standards referenced, not reproduced: DO-178C / ARP4754A / ARP4761A text is
  proprietary (RTCA/SAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
