---
name: planning
description: "Use when planning DO-178C software certification: produce the PSAC (Plan for Software Aspects of Certification), determine the software level / DAL (A-E), and scope planning-phase artifacts. Trigger: PSAC, DAL determination, software level, DO-178C planning, certification planning, ARP4754A development assurance."
license: Apache-2.0
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do178c
  tags: [do-178c, dal, psac, certification, arp4754a, arp4761a, software-levels]
  version: 0.1.0
  author: AeroSkills
  standards: [DO-178C, ARP4754A, ARP4761A]
  compliance: STANDARDS-REF
  gated: false
---

# DO-178C Planning (avionics/do178c/planning)

Skeleton. Full body lands with harness gate 3 by 2026-09-04 (DAL A-E
determination test per ARP4754A/ARP4761A).

## When to use

Use when the task is DO-178C planning-phase work: drafting a PSAC,
determining the software level (DAL) for a function or item, or scoping
planning-phase artifacts (PSAC, SDP, SVP, SCM, SQA plans).

## Domain quick reference

- Software levels (DO-178C): A = Catastrophic, B = Hazardous, C = Major,
  D = Minor, E = No safety effect.
- ARP4754A splits development assurance: FDAL (function) vs IDAL (item).
- ARP4761A propagates failure-condition severity to DAL.
- Coverage depth scales with DAL: A = 100% MC/DC, B = 100% decision,
  C = 100% statement, D = none required.
- Accepted means of compliance: AC 20-115D (software), AC 20-174 (ARP4754A).

## Workflow (skeleton)

1. Confirm certification basis and applicable standards.
2. Determine failure-condition severity per ARP4761A (FHA/PSSA inputs).
3. Allocate DAL / FDAL / IDAL per ARP4754A + ARP4761A.
4. Map DAL to DO-178C software level and objectives tables.
5. Draft PSAC and planning-phase artifacts.

## Pitfalls

- DAL from severity alone without FDAL/IDAL split.
- Coverage depth mismatched to level (A requires MC/DC, not statement).
- Traceability gaps (no derived requirements).

## Compliance

- Standards referenced, not reproduced: DO-178C / ARP4754A / ARP4761A text is
  proprietary (RTCA/SAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
