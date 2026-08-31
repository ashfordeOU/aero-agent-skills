---
name: safety-assessment
description: "Use when planning or conducting the civil-aircraft safety assessment process per ARP4761A: classify failure-condition severity, run the FHA/PSSA/SSA sequence at the right design maturity, and scope the analysis set (FTA, FMEA, CCA) that scales with the development assurance level. Severity propagates into assurance (A = Catastrophic through E = No safety effect), the assessment plan is part of the program planning artifacts, and common-cause analysis covers zonal, particular-risk, and common-mode risks. Trigger: ARP4761A safety assessment, FHA, PSSA, SSA, failure condition severity, fault tree analysis, FMEA, common cause analysis, safety assessment plan."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
  - id: arp4754a
    reference-only: true
gated: false
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: arp4761a
  tags: [arp4761a, fha, pssa, ssa, cca, fta, fmea, safety-assessment]
  version: 0.1.0
  author: AeroSkills
---

# ARP4761A Safety Assessment (arp4761a/safety-assessment)

Use when the task is aircraft or system safety assessment per
ARP4761A: severity classification, the FHA-PSSA-SSA sequence, and the
analysis set for a certification program.

## Domain quick reference

- FHA (functional hazard assessment) identifies failure conditions and
  classifies severity; PSSA (preliminary system safety assessment)
  shows the proposed architecture meets safety requirements; SSA
  (system safety assessment) confirms the implemented system does.
- Severity propagates into development assurance: A = Catastrophic,
  B = Hazardous, C = Major, D = Minor, E = No safety effect.
- FTA (fault tree) and FMEA (failure modes and effects) are the
  standard techniques; CCA (common cause analysis) covers zonal,
  particular-risk, and common-mode risks (ZSA/PRA/CMA).
- The safety assessment plan is one of the program planning artifacts
  and scales with the development assurance level.

## Workflow

1. Scope the safety assessment plan for the program and confirm the
   certification basis.
2. Classify failure-condition severities via the FHA.
3. At the proposed-architecture stage, run the PSSA to show safety
   requirements are met.
4. Select the analysis set (FTA/FMEA, CCA at the highest levels).
5. After implementation, run the SSA and close the safety
   requirements.

## Pitfalls

- Running the SSA before the architecture is fixed (sequence error).
- Dropping CCA at levels A/B where common-cause analysis is expected.
- Severity assigned without the FHA-to-PSSA-to-SSA chain.
- Analysis set fixed without consulting the approved safety plan.

## Behavior contract (gate 3)

The severity, phase, and analysis-set logic is exercised by the gate 3
contract test: scripts/test_safety_assessment.py against
scripts/safety_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_safety_assessment.py

## Compliance

- Standards referenced, not reproduced: ARP4761A / ARP4754A text is
  proprietary (SAE); summary-only per standards-map.yaml and brief 06.
- Revision note: ARP4754B (2023) supersedes ARP4754A; this skill keys to
  ARP4754A as the certification-baseline revision (FAA AC 20-174 cites A);
  see standards-map.yaml arp4754a.revision_decision.
- compliance: STANDARDS-REF, gated: false.
