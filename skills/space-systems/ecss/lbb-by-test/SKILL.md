---
name: lbb-by-test
description: "Use when assess the Leak-Before-Break (LBB) condition for pressurized lines, fittings, or vessels under ECSS-E-ST-32C clauses 5.3.3–5.3.4 by means of coupon or full/sub-scale physical test evidence: select specimens representative of flight hardware, apply a surface flaw at the NDE detection limit, cycle under the design load spectrum to through-wall crack formation, confirm the through-wall (leak) crack length is shorter than the critical burst crack length, and verify proof and burst pressure factors meet the clause requirements. Trigger: ecss, e-st-32-structures-scope, lbb, leak-before-break, fracture-mechanics, pressure-vessel, coupon-test, sub-scale-test, damage-tolerance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, lbb, leak-before-break, fracture-mechanics, pressure-vessel, coupon-test, sub-scale-test, damage-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — LBB Demonstration by Test (space-systems/ecss/lbb-by-test)

Use when the task is to assess the Leak-Before-Break (LBB) condition under
ECSS-E-ST-32C clauses 5.3.3–5.3.4 using coupon tests to establish crack-growth
material properties, and full or sub-scale tests to demonstrate that any
through-wall crack forms as a detectable leak before the crack length reaches
the critical value for burst.

## Domain quick reference

- LBB is a damage-tolerance strategy for pressurized lines and vessels: the
  design is accepted only if a crack growing under the applied load spectrum
  will penetrate the full wall thickness — producing a detectable leak — while
  still shorter than the critical crack length at which fast fracture or burst
  would occur.
- Clause 5.3.3 covers coupon-level testing used to obtain material fatigue
  crack-growth properties (crack-growth rate and fracture toughness) under
  the relevant environment and stress ratio. Coupon data establishes the inputs
  for fracture mechanics analysis but does not by itself demonstrate LBB at the
  system level.
- Clause 5.3.4 covers full-scale or sub-scale specimen tests that directly
  demonstrate LBB behaviour: a pre-flawed specimen is cycled under a
  representative load spectrum until a through-wall (leak) crack forms, then
  loaded further to burst to confirm the LBB margin exists in the hardware.
- The fundamental LBB condition: the through-wall crack length at first leak
  must be strictly less than the critical crack length at burst pressure. The
  LBB margin (ratio of critical crack length to through-wall crack length) must
  exceed 1.0.
- Pressure factors are verified against the Maximum Expected Operating Pressure
  (MEOP): burst factor >= 1.5 × MEOP for metallic lines; proof factor >= 1.0 ×
  MEOP minimum. Sub-scale specimens must be at or above 50% of flight scale to
  be accepted without additional justification.

## Workflow

1. Categorize each test specimen as coupon, sub-scale, or full-scale. Reject
   any specimen type not in that set before proceeding.
2. For coupon tests (clause 5.3.3): record the measured crack-growth rate
   (mm/cycle) and fracture toughness (MPa√m) under the specified stress ratio
   and environment. These values feed the fracture mechanics model that
   determines the critical crack length and the cycles to through-wall crack.
3. Estimate cycles to through-wall crack: compute the remaining wall depth
   (wall thickness minus initial NDE flaw depth) divided by the mean measured
   crack-growth rate. Flag if the estimated life is shorter than the design
   fatigue life.
4. For sub-scale or full-scale tests (clause 5.3.4): confirm the specimen scale
   factor is >= 0.5 for sub-scale or 1.0 for full-scale. Verify the initial
   surface flaw depth equals the NDE detection limit for the inspection method
   to be used on flight hardware.
5. Check the LBB condition: the through-wall crack length recorded at first leak
   must be less than the critical crack length derived at burst pressure. Compute
   the LBB margin; a margin at or below 1.0 is a finding.
6. Verify the burst and proof pressure factors against MEOP: burst >= 1.5 ×
   MEOP, proof >= 1.0 × MEOP. Flag any factor below the threshold as a
   non-compliance.
7. Aggregate findings: the LBB demonstration passes only when the LBB condition
   is met, the pressure factors are within limits, and the specimen type and
   scale are acceptable. Any open finding blocks the demonstration.

## Pitfalls

- Using coupon data alone to claim system-level LBB demonstration — clause
  5.3.4 requires a sub-scale or full-scale specimen test to demonstrate LBB
  behaviour at the hardware level; coupon data is an input, not the
  demonstration itself.
- Applying the burst-pressure critical crack length to the proof-pressure
  condition — the critical crack length changes with applied stress; if the LBB
  check is run at proof pressure rather than burst pressure, the critical crack
  length is underestimated and the LBB condition may appear falsely more
  conservative.
- Accepting a sub-scale specimen below 50% scale without additional
  justification — size effects on crack-tip constraint and leak detection
  sensitivity can invalidate the result at very small scales.
- Treating a measured LBB margin exactly at 1.0 as a pass — at margin = 1.0
  the through-wall crack length equals the critical crack length; any scatter
  in the test data or analysis means the condition is not reliably met and
  further margin is required.
- Omitting the NDE detection limit from the initial flaw size selection — if
  the initial flaw is smaller than what NDE can reliably detect on flight
  hardware, the test does not represent the worst-case in-service condition.

## Behavior contract (gate 3)

The specimen categorization, LBB condition check, margin computation, pressure
factor verification, and cycle estimation logic are exercised by the gate 3
contract test: scripts/test_lbb_by_test.py against scripts/lbb_by_test_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_lbb_by_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
