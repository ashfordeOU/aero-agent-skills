---
name: systems-planning
description: "Use when you must plan aircraft and system development per ARP4754A: allocate FDAL to functions and IDAL to items from failure-condition severity, scope the certification plan and system development plan, and interface development planning with the ARP4761A safety assessment process. An item's IDAL equals the highest FDAL among the functions it implements, and safety assessment depth scales with the development assurance level. Trigger: ARP4754A systems planning, FDAL allocation, IDAL allocation, certification plan, system development plan, safety assessment interface."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: arp4754a
  tags: [arp4754a, arp4761a, fdal, idal, planning, safety, certification]
  version: 0.1.0
  author: AeroSkills
---

# ARP4754A Systems Planning (arp4754a/systems-planning)

Use when the task is aircraft or system development planning per
ARP4754A: assurance allocation and the planning artifacts of a system
certification program.

## Domain quick reference

- ARP4754A assigns FDAL to functions and IDAL to items; an item's IDAL
  is the highest FDAL among the functions it implements.
- ARP4761A propagates failure-condition severity into development
  assurance (A = Catastrophic ... E = No safety effect).
- Planning artifacts: certification plan, system development plan, and
  safety assessment plan (when safety-significant functions exist).
- Safety assessment depth scales with the development assurance level:
  A/B/C run the full FHA-PSSA-SSA chain; D/E stay at baseline
  identification (confirm against the approved plan).
- The certification plan identifies the applicable certification basis
  and the means of compliance for each area.

## Workflow

1. Identify the certification basis and applicable regulations.
2. Determine failure-condition severities (ARP4761A FHA inputs).
3. Allocate FDAL to functions; derive IDAL for items.
4. Scope the certification plan, system development plan, and safety
   assessment plan.
5. Interface development planning with the safety assessment process
   and downstream software/hardware planning.

## Pitfalls

- IDAL below the highest FDAL of the implemented functions.
- Safety assessment plan missing for safety-significant functions.
- Severity mapped to DAL without the FDAL/IDAL split.
- Planning without the certification basis identified.

## Behavior contract (gate 3)

The FDAL/IDAL and planning-artifact logic is exercised by the gate 3
contract test: scripts/test_systems_planning.py against
scripts/systems_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_systems_planning.py

## Revision note (ARP4754A vs ARP4754B)

Keyed to ARP4754A by design: A is the certification-baseline revision:
FAA AC 20-174 and AC 25-1309 recognize ARP4754A as an acceptable means of
compliance for development assurance, and the DO-178C/DO-254 ecosystem
references A. ARP4754B (SAE, revised 2023-12) supersedes A; it is the
update (alignment with ARP4761A, no significant change in development
principles). Skills key to A to match current TC/STC certification-baseline
practice. See standards-map.yaml arp4754a.revision_decision.

## Compliance

- Standards referenced, not reproduced: ARP4754A / ARP4761A text is
  proprietary (SAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
