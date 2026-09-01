---
name: verification-planning
description: "Use when you must plan system level verification per ARP4754A: assign a verification method (test, analysis, demonstration, or inspection) to each requirement, check the method is acceptable for the development assurance level, require independent verification where the level demands it, and score verification coverage, including the derived requirements, against the safety assessment outputs before the evidence is released. Produces the method register, the independence flag, and the coverage closure verdict that gate the system verification plan. Trigger: verification planning, verification method, test analysis demonstration inspection, derived requirement coverage, arp4754a verification."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: true
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4754a
  tags: [verification-planning, verification-method, derived-requirement, verification-coverage, method-register, system-verification-plan]
  version: 0.1.0
  author: AeroSkills
---

# ARP4754A System Verification Planning (systems-engineering-safety/arp4754a/verification-planning)

Use when the task is system level verification planning per ARP4754A:
method selection, independence, and coverage closure before the
verification evidence is released.

## Domain quick reference

- Verification asks whether the implementation satisfies the
  requirements (built right); validation asks whether the right
  requirements were captured. ARP4754A treats the two as separate
  processes with separate plans and records.
- Verification methods (common methodology): test, analysis,
  demonstration, and inspection. Test exercises the item dynamically,
  analysis uses analytical or modeling evidence, demonstration shows
  operation or function qualitatively, and inspection checks physical
  characteristics by examination or measurement.
- Method acceptability scales with the development assurance level.
  Levels A and B, the most safety significant, restrict planning to the
  rigorous methods (test and analysis); level C adds demonstration, and
  levels D and E accept all four methods.
- Independence of the verification activity is required at levels A and
  B, matching the independence rule for validation.
- Derived requirements, which arise from design decisions rather than
  from higher level requirements, carry the same verification
  obligation: each one needs an assigned method, evidence, and a place
  in the trace matrix.
- Verification planning consumes the failure condition and safety
  assessment outputs: the severity drives the assurance level, and the
  level drives the acceptable methods and the independence need.
- Coverage closure: every requirement, allocated or derived, verified by
  at least one acceptable method with evidence before the verification
  results release to the certification data.

## Workflow

1. Collect each requirement with its verification status, method, and
   development assurance level.
2. Normalize and confirm the method with verification_method_ok.
3. Confirm the method is acceptable for the level with method_allowed
   and recommended_methods.
4. Check the independence need with independence_required.
5. Score the coverage with coverage_ratio and coverage_complete,
   including the derived requirements with
   derived_requirement_coverage_ok.
6. Close the plan with verification_plan_closure and gate the evidence
   release on the verdict.

## Pitfalls

- Treating verification and validation as one step: ARP4754A keeps them
  separate, and verification evidence does not substitute for validation
  findings.
- Assigning inspection or demonstration at level A or B, where the
  method is not acceptable for the assurance level.
- Forgetting derived requirements in the coverage count: they carry the
  same verification obligation as allocated requirements.
- Counting simulation as a separate top level method: simulation and
  modeling are forms of analysis evidence within the four method set.
- Scoring coverage over assigned methods instead of verified-with-
  evidence requirements, which overstates closure.
- Releasing verification results with open items on the plan.

## Behavior contract (gate 3)

The method, acceptability, independence, and coverage logic is exercised
by the gate 3 contract test: scripts/test_verification_planning.py
against scripts/verification_planning_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_verification_planning.py

## Compliance

- Standards referenced, not reproduced: ARP4754A text is proprietary
  (SAE); the verification method set and the level based acceptability
  guidance are common systems-engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: true.
