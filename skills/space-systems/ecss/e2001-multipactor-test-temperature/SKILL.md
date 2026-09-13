---
name: e2001-multipactor-test-temperature
description: "Use when plan and grade a multipactor-test campaign run at the temperature-extremes defined for the critical-gap region under ECSS-E-ST-20-01C clause 6.3: derive cold and hot qualification setpoints from the predicted thermal range plus qualification-margin, expand the critical-gap with temperature, form the frequency-gap-product at each extreme, read the first-order breakdown-threshold off the susceptibility trend, convert applied RF-power into a peak gap-voltage, name the worst-case extreme, and confirm the tested setpoints covered both extremes after a stabilising thermal-soak. Trigger: ecss, e-st-20-01c, multipactor-test-temperature, critical-gap-region, temperature-extremes, frequency-gap-product, breakdown-threshold-voltage, thermal-soak-stabilisation."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-test-temperature, multipactor-test-temperature, critical-gap-region, temperature-extremes, frequency-gap-product, thermal-soak-stabilisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Test Temperature Extremes (space-systems/ecss/e2001-multipactor-test-temperature)

Use when the task is the temperature coverage of ECSS-E-ST-20-01C
clause 6.3 -- running the multipactor-test at the extremes defined for
the critical-gap region rather than at ambient, because the gap that
sets the discharge threshold is itself a function of temperature.

## Domain quick reference

- The test extremes are not the predicted extremes. Cold and hot
  setpoints come from the predicted thermal range widened by the
  qualification-margin on both sides, so a campaign that runs at the
  prediction alone has not covered the requirement.
- The critical-gap moves with temperature. Linear expansion of the
  surrounding structure opens the gap when heated and closes it when
  cooled, for a positive effective expansion coefficient; a negative
  coefficient reverses that. The relevant gap is the one at the test
  temperature, not the drawing dimension at room temperature.
- Susceptibility is governed by the frequency-gap-product, not the gap
  alone. A smaller gap at a fixed frequency moves the product down the
  trend, and the first-order breakdown-threshold falls with it. That is
  why the extreme with the smaller gap normally carries the least
  margin even though the RF-power is unchanged.
- Margin is a voltage ratio expressed in decibels: the applied peak
  voltage across the gap comes from the RF-power carried by the line
  and the line impedance, and the margin is the threshold over that
  applied voltage. The worst-case extreme is whichever of the two
  leaves the smaller margin, and it is the one the verification
  argument rests on.
- A setpoint reached is not a setpoint held. The item has to soak long
  enough to stabilise and its drift during the run has to stay inside
  tolerance, otherwise the gap during the run was not the gap the
  analysis assumed.

## Workflow

1. Derive the cold and hot qualification setpoints from the predicted
   minimum and maximum plus the qualification-margin. Reject an
   inverted predicted range, a negative margin, and a cold setpoint
   that falls below absolute zero.
2. For each extreme, compute the critical-gap from the reference gap,
   the effective expansion coefficient and the temperature difference
   from the reference. Reject an expansion model that closes the gap.
3. Form the frequency-gap-product at each extreme and read the
   first-order breakdown-threshold off the susceptibility trend by
   log-log interpolation. Reject a product outside the tabulated range
   rather than extrapolating past it.
4. Convert the applied RF-power and line impedance into the peak gap
   voltage, and express the margin as the decibel ratio of threshold
   to applied voltage.
5. Compare each margin against the required margin and name the
   worst-case extreme as the lower of the two.
6. Check that the tested setpoints actually landed on both extremes
   within the setpoint tolerance, and that the soak duration and the
   in-run drift met their requirements.
7. Aggregate: the campaign is not clause 6.3 compliant until both
   extremes hold margin, both are covered by a tested setpoint, and
   the thermal-soak stabilised the item.

## Pitfalls

- Testing at ambient and arguing the extremes by analysis alone. The
  clause asks for the test to be run at the extremes; an ambient run
  plus an extrapolation is a different verification route.
- Using the drawing gap at every temperature. The gap at the cold
  extreme is the one that sets the worst-case threshold, and it is not
  the dimension on the drawing.
- Assuming the hot extreme is always worst because hot is worse for
  most other failure modes. For a positive expansion coefficient the
  cold extreme closes the gap and lowers the threshold, so the sign of
  the coefficient decides which extreme governs.
- Extrapolating the susceptibility trend beyond its tabulated range and
  quoting a threshold for a frequency-gap-product it never covered.
- Recording a setpoint as covered because the chamber was commanded
  there, without checking the soak and the in-run drift.
- Letting an exact-boundary setpoint or margin read as a violation. A
  deviation computed as a difference of temperatures can land a few
  units in the last place beyond the tolerance, so the comparison
  absorbs the representation error rather than widening the tolerance.

## Behavior contract (gate 3)

The qualification-extreme, gap-expansion, frequency-gap-product,
breakdown-threshold, margin, worst-case, soak and coverage logic is
exercised by the gate 3 contract test:
`scripts/test_e2001_multipactor_test_temperature.py` against
`scripts/e2001_multipactor_test_temperature_logic.py` (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_multipactor_test_temperature.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
