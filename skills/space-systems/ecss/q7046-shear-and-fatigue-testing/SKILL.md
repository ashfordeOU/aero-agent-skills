---
name: q7046-shear-and-fatigue-testing
description: "Determine whether a threaded fastener application owes shear testing, fatigue testing or both, size the shear allowable from the loaded plane, and judge the results that come back. Use when a joint is shear loaded or cyclically loaded and someone has to say what testing the application calls for and whether the lot passed: pick the plane the shear actually crosses, count single against double shear, derive the allowable from the property class, then score each fatigue specimen as a failure, a pass or a run-out and refuse a verdict on too small a set. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-shear-test-requirement, fastener-double-shear-plane, fastener-shear-allowable-load, fastener-fatigue-runout, fastener-fatigue-specimen-count."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-shear-and-fatigue-testing, fastener-shear-test-requirement, fastener-double-shear-plane, fastener-shear-allowable-load, fastener-fatigue-runout, fastener-fatigue-specimen-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Shear and Fatigue Testing (space-systems/ecss/q7046-shear-and-fatigue-testing)

Use when the task is the conditional part of the testing clause of
ECSS-Q-ST-70-46: shear and fatigue testing are owed by the application
rather than by every fastener, so the first question is whether this
joint calls for them and the second is what the results have to reach.

## Domain quick reference

- Shear and fatigue are application-driven tests. A tension-loaded,
  statically loaded joint on non-structural hardware owes neither; a
  shear-loaded joint owes shear, a cyclically loaded joint owes
  fatigue, and a fracture-critical fastener owes both regardless of how
  gentle the duty looks on paper.
- The shear allowable depends on which plane the joint puts the shear
  through. A joint designed so the plate interface crosses the plain
  shank uses the full shank section; a joint where the interface lands
  on the threads uses the much smaller minor-diameter section. Assuming
  the shank plane when the design puts the threads in shear overstates
  the allowable by a wide margin.
- Single and double shear are the same material in a different fixture.
  Double shear crosses two planes, so the load the fastener carries is
  twice the single-plane allowable while the stress in the fastener is
  unchanged. Reporting a double-shear result against a single-shear
  allowable makes a marginal fastener look comfortable.
- Shear strength is a fraction of tensile strength, and the fraction
  belongs to the material family rather than to the fastener. A
  stainless fastener and an alloy-steel one at the same ultimate stress
  do not have the same shear allowable.
- A fatigue specimen has three outcomes, not two. Below the required
  life it failed; at or beyond the run-out limit it survived the test
  and is a run-out; between the two it passed on its own cycles. A
  run-out counted as a failure throws away a valid result, and a
  run-out counted as an exact life invents one.
- A fatigue result is a set result. Scatter is the property being
  measured, so a set below the minimum specimen count has no verdict
  to give, however good the individual numbers look.

## Workflow

1. Read the application: load mode, criticality and whether the duty is
   cyclic. Refuse an unrecognised load mode rather than defaulting it
   to tension.
2. Decide the testing owed and record why each test was called for, so
   a reviewer can see the rule that triggered it.
3. Validate the geometry and pick the shear plane the joint actually
   loads; form the plane area from the shank diameter or from the minor
   diameter as that choice dictates.
4. Multiply the plane area by the shear strength of the property class
   and by the number of planes to get the allowable load.
5. Compare each measured shear load with the allowable, absorbing
   representation error at the boundary with a named tolerance rather
   than by trimming the allowable.
6. Score each fatigue specimen against the required life and the
   run-out limit, categorized as failed, passed or run-out.
7. Roll up: the worst non-run-out life, the run-out count, and a refusal
   to give a verdict when the set is smaller than the minimum.

## Pitfalls

- Sizing the shear allowable on the shank when the joint puts the
  threads in the shear plane. The minor diameter is several percent
  smaller and its area is smaller again, so the error is not a rounding
  matter.
- Comparing a double-shear test load with a single-shear allowable. The
  fixture doubled the load path, and the comparison has to double with
  it.
- Using the tensile strength as the shear strength. The shear fraction
  is material-family property and omitting it flatters every result.
- Recording a run-out as a failure at the run-out cycle count. The
  specimen survived, and the only honest statement about its life is
  that it exceeded the limit.
- Calling a fatigue programme passed on one or two specimens. Fatigue
  scatter is what the test measures, and a set under the minimum has
  not measured it.
- Deciding fatigue is not owed because the load looks small. The trigger
  is cyclic duty and criticality, not amplitude.

## Behavior contract (gate 3)

The requirement rules, shear plane selection, single against double
shear, the allowable derivation, the three-way fatigue outcome and the
minimum-set refusal are exercised by the gate 3 contract test:
scripts/test_q7046_shear_and_fatigue_testing.py against
scripts/q7046_shear_and_fatigue_testing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_shear_and_fatigue_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
