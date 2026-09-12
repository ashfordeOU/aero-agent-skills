---
name: e20-charging-programme-analysis-and-testing
description: "Use when maintain the analysis and test planning inside a spacecraft charging protection programme under ECSS-E-ST-20C clause 6.3.4.2: categorize each planned activity as a charging analysis task or a charging test task, derive the mandatory task set from the charging regime the item is exposed to, report every required task that is absent or left unplanned, compute the steady-state field a penetrating electron flux drives into a dielectric against its derated breakdown strength, derive the charge bleed-off time constant against the permitted limit, and confirm every planned test severity envelopes the worst case the analysis predicts. Trigger: ecss, e-st-20c-clause-6-3-4-2, spacecraft-charging-protection-programme, charging-analysis-planning, charging-test-planning, deep-dielectric-charging, electrostatic-discharge-test-environment, bleed-off-time-constant, differential-potential-onset."
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
  tags: [ecss, e-st-20-electrical-scope, e20-charging-programme-analysis-and-testing, spacecraft-charging-protection-programme, charging-analysis-planning, charging-test-planning, deep-dielectric-charging, bleed-off-time-constant, differential-potential-onset]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Charging Programme Analysis and Testing (space-systems/ecss/e20-charging-programme-analysis-and-testing)

Use when the task is the clause 6.3.4.2 planning content of
ECSS-E-ST-20C -- keeping a spacecraft charging protection programme
carrying both a predictive workstream and a hardware workstream, sized
to the charging environment the item actually sees, with the planned
test conditions still bounding what the prediction says will happen.

## Domain quick reference

- A charging protection programme holds two families of activity and
  the clause asks for both. The predictive family covers absolute and
  differential potential work, the internal field a penetrating
  electron flux builds inside a dielectric, the energy a discharge
  would release, and the path charge takes to drain away. The hardware
  family covers electron-beam charging of a coupon, discharge
  susceptibility of a unit, measurement of the bleed-off resistance,
  screening of dielectric breakdown, and transient injection on the
  harness. An activity that belongs to neither family is not a
  programme task and is rejected before the plan is graded.
- The mandatory task set follows the charging regime. A geostationary
  surface-charging item, an auroral low-orbit item, an internally
  charged dielectric and a solar-array triple junction each draw a
  different combination, and every regime draws at least one task from
  each family -- the clause cannot be closed by prediction alone, nor
  by testing an item whose exposure was never predicted. A required
  task that is absent from the plan, carried with no status, or parked
  as not planned is the same finding: the programme does not cover it.
- The internal field in a dielectric at steady state is the penetrating
  current density multiplied by the bulk resistivity of the material.
  It is compared against the breakdown strength derated by a safety
  factor, not against the raw strength. The same resistivity, with the
  material permittivity, sets the bleed-off time constant: how long a
  deposited charge takes to drain. A highly resistive material is the
  worst of both -- it builds a larger field and holds it longer.
- The differential potential between a surface and the structure it
  sits on is what drives a discharge, and only its magnitude matters;
  charging potentials are normally negative and the sign carries no
  information for the onset check.
- The consistency rule between the two families is one-directional:
  every severity parameter the analysis predicts must be met or
  exceeded by the planned test. A test planned below the predicted
  severity does not qualify the item, and a predicted parameter the
  test plan never names is an uncovered prediction, reported on its
  own terms rather than folded into the severity comparison.

## Workflow

1. Categorize every activity the programme plans as an analysis task
   or a test task; reject an activity that is neither before the plan
   is graded.
2. Derive the mandatory task set from the item's charging regime and
   list every required task the plan does not carry, treating an
   absent task, a null status and a parked task alike.
3. Compute the steady-state dielectric field from the penetrating
   current density and the bulk resistivity, and compare it against
   the breakdown strength divided by the safety factor.
4. Derive the bleed-off time constant from the relative permittivity
   and the same bulk resistivity, and compare it against the drain
   time the programme permits.
5. Take the magnitude of the surface-to-structure potential difference
   and compare it against the discharge-onset threshold for that
   surface pair.
6. For every severity parameter in the analysis worst case, confirm
   the test plan carries the parameter and plans it at or above the
   predicted value; report an absent parameter separately from an
   under-severe one.
7. Aggregate the planning, dielectric, bleed-off, differential and
   envelope findings; the item is covered only when all five lists are
   empty.

## Pitfalls

- Counting a long list of predictive work as a complete programme.
  Every regime in the clause draws a hardware task as well, and a plan
  with no test task is incomplete however deep the modelling goes.
- Treating a task named on the plan with no status as planned. A row
  with no commitment behind it is indistinguishable from an absent row
  for the purpose of the clause, and both are findings.
- Comparing the internal field against the raw breakdown strength of
  the datasheet rather than the derated allowable; the safety factor
  is what separates a qualification margin from a coin flip on a
  material property that scatters with temperature and dose.
- Reading a low field as sufficient evidence and skipping the drain
  check. Field magnitude and drain time come from the same resistivity
  but answer different questions, and a material can pass the field
  check while holding charge far longer than the programme allows.
- Signing the surface potential into the onset comparison. Both
  potentials are usually negative, the differential is a magnitude,
  and carrying the sign through flips a real exceedance into an
  apparent pass.
- Planning the charging test at the predicted severity and calling the
  pair consistent when the value is a sum or a product; a physically
  equal case can land a few representation units on the wrong side, so
  the equality is absorbed in the comparison rather than by widening
  the planned severity.

## Behavior contract (gate 3)

The task categorization, regime task-set, unplanned-task, dielectric
field, bleed-off time constant, differential potential and
test-envelope logic is exercised by the gate 3 contract test:
scripts/test_e20_charging_programme_analysis_and_testing.py against
scripts/e20_charging_programme_analysis_and_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_charging_programme_analysis_and_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
