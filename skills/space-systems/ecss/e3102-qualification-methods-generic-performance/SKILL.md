---
name: e3102-qualification-methods-generic-performance
description: "Evaluate how each qualification requirement for two-phase heat transport equipment is verified and whether the generic performance demonstration actually closes, per ECSS-E-ST-31-02C clauses 5.5.3, 5.5.4 and 5.5.5.1. Use when the task is allocating test, analysis or analysis-supported-by-test to a requirement and rejecting a proposal weaker than the requirement warrants, sizing the governing mechanical design load and its margin of safety, comparing demonstrated cycles against a scatter-factored safe-life target, and deciding whether a pressure boundary leaks before it bursts. Trigger: ecss, e-st-31-02c, qualification-method-allocation, worst-case-mechanical-load, margin-of-safety, safe-life-scatter-factor, leak-before-burst, critical-flaw-depth."
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
  tags: [ecss, e-st-31-02-two-phase-scope, e3102-qualification-methods-generic-performance, qualification-method-allocation, worst-case-mechanical-load, safe-life-scatter-factor, leak-before-burst, critical-flaw-depth]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Qualification Methods and Generic Performance (space-systems/ecss/e3102-qualification-methods-generic-performance)

Use when the task is the method allocation and generic performance
demonstration of ECSS-E-ST-31-02C clauses 5.5.3, 5.5.4 and 5.5.5.1 --
deciding how each qualification requirement is closed, and then closing
the three demonstrations every two-phase item owes regardless of what it
is: worst-case mechanical loads, safe-life or fatigue, and a pressure
boundary that leaks before it bursts.

## Domain quick reference

- Verification methods form a strength ordering, not a menu:
  review-of-design, inspection, analysis, analysis-supported-by-test,
  test. A proposal at or above the strength the requirement warrants is
  adequate; below it is a finding. Writing the ordering down is what
  makes "we will analyse it instead" a gradeable statement rather than a
  negotiation.
- What a requirement warrants comes from its kind and its criticality.
  Anything safety-critical is demonstrated by test. Performance and
  leak-tightness go to test because neither is predictable to the
  accuracy the requirement states. A structural requirement can go to
  analysis-supported-by-test, but only where correlated test evidence
  exists; without correlation the model is an assertion. Dimensional
  properties are inspectable on the delivered article, and documentation
  requirements close on review of the design data.
- The mechanical demonstration is against the worst case, not the
  nominal. The design load is the limit load times the design factor,
  and the governing case is the one with the highest design load -- not
  the highest limit load, because a case can carry its own factor. The
  margin of safety is the allowable over the design load, less one, and
  zero is a pass.
- Safe life is a cycle count with a scatter factor on it. The
  demonstration has to cover the service life multiplied by that factor;
  a demonstration equal to the service life alone covers none of the
  material scatter the factor exists to absorb.
- Leak-before-burst is a fracture-mechanics property of the boundary, not
  a test result. The critical flaw depth implied by the fracture
  toughness and the hoop stress has to exceed the wall thickness: then a
  growing flaw reaches the outer surface and vents while it is still
  stable. Below the wall thickness the flaw goes unstable inside the
  wall and the boundary bursts.
- Hoop stress here is the thin-wall value, which is only meaningful while
  the wall is thin against the radius. A thick-wall tube needs the thick
  wall relation, so the thin-wall function refuses rather than returning
  a quietly wrong number.

## Workflow

1. Validate each requirement: an identifier, a known kind, an explicit
   criticality flag, and an explicit correlated-evidence flag where the
   kind is structural.
2. Allocate the warranted method from kind and criticality, and record
   the rationale alongside it so the allocation can be argued with.
3. Compare the proposed method on the strength ordering and raise a
   finding naming both methods where the proposal is weaker.
4. Size every load case: design load equals limit load times the case
   factor, falling back to the programme factor. Retain the case with
   the highest design load, breaking an exact tie on the case name so
   the result is reproducible.
5. Reduce the allowable against the governing design load to a margin of
   safety, and treat an exact zero as compliant by absorbing only the
   representation error in a named tolerance.
6. Multiply the service life by the scatter factor and compare the
   demonstrated cycles with the product, reporting the coverage ratio
   rather than only the verdict.
7. Compute the hoop stress, the critical flaw depth from the fracture
   toughness and the geometry factor, and the depth-to-thickness ratio;
   compare it with the required ratio.
8. Aggregate all four into one verdict, with every shortfall named.

## Pitfalls

- Allocating analysis to a performance requirement because a model
  exists. The model's accuracy is the thing in question, and an
  uncorrelated model closes nothing.
- Picking the governing load case on limit load. A lower limit load with
  a higher case-specific factor can govern, and the case that governs is
  the one with the highest design load.
- Reading a margin of safety of exactly zero as a failure. Zero is the
  definition of adequate; only the floating-point representation of the
  quotient is absorbed, never the allowable.
- Demonstrating the service life and calling safe life closed. The
  scatter factor multiplies the life; without it the demonstration
  covers the mean article and nothing else.
- Comparing critical flaw depth with the flaw found in inspection rather
  than with the wall thickness. Leak-before-burst is about whether a
  flaw can reach the outer surface while stable, and the wall thickness
  is the distance that matters.
- Using the thin-wall hoop stress on a thick-wall boundary. The number
  comes out low, and the leak-before-burst verdict comes out optimistic.

## Behavior contract (gate 3)

The requirement validation, method allocation and strength grading, load
case factoring and worst-case retention, margin of safety, scatter-factored
safe-life comparison, thin-wall hoop stress, critical flaw depth and
leak-before-burst verdict are exercised by the gate 3 contract test:
scripts/test_e3102_qualification_methods_generic_performance.py against
scripts/e3102_qualification_methods_generic_performance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3102_qualification_methods_generic_performance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
