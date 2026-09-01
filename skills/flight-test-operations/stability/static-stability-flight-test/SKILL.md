---
name: static-stability-flight-test
description: "Evaluate the static stability flight test results: fit the trim curve to the elevator angle versus speed points, derive the trim curve slope, locate the stick fixed neutral point from the slope, estimate the static margin, and assess the elevator angle per g from the incremental elevator angle per load factor step. Produces the trim curve fit, the slope, the stick fixed neutral point, the static margin, and the stability verdict that gate the static stability demonstration. Use when the task is static stability flight testing, trim curve reduction, neutral point location, or static margin estimation. Trigger: static stability, trim curve, elevator angle, stick fixed, neutral point, static margin, elevator angle per g."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: stability
  tags: [static-stability, trim-curve, elevator-angle, neutral-point, static-margin, stick-fixed, stick-free, elevator-angle-per-g, flight-test]
  version: 0.1.0
  author: AeroSkills
---

# Static Stability Flight Test (flight-test-operations/stability/static-stability-flight-test)

Use when the task is a static stability flight test: trim curve
reduction from pitch control position versus speed, neutral point
location, and static margin assessment.

## Domain quick reference

- The trim curve is the elevator angle (pitch control position)
  needed to hold steady level trim at each test speed. Each speed V
  converts to a lift coefficient CL = 2 W / (rho V^2 S), so the test
  points become elevator angle versus CL.
- The trim curve slope b = d(delta_e)/dCL comes from a least squares
  fit delta_e = a + b CL. A negative slope is the signature of a
  statically stable aircraft: less up elevator is needed as speed
  increases.
- Stick fixed neutral point from the slope, the cg position h, and
  the elevator control power Cm_delta_e (per radian):
  h_n = h + b Cm_delta_e (pi/180), with static margin SM = h_n - h. A
  positive margin is stable, a negative margin is unstable (flag),
  and zero is neutral.
- Stick free neutral point shifts forward of the stick fixed value by
  (Cm_delta_e Ch_alpha) / (CL_alpha Ch_delta_e) from the free
  elevator hinge model (Ch_alpha and Ch_delta_e are the hinge moment
  derivatives, CL_alpha the lift curve slope, all per radian).
- Elevator angle per g: d(delta_e)/dn = (180/pi) CL SM / Cm_delta_e
  in degrees per g. A stable aircraft shows trailing-edge-up elevator
  movement with increasing load factor (negative value), reported as
  its magnitude.

## Workflow

1. Collect the trimmed elevator angle at each steady level speed.
2. Convert the speeds to lift coefficients with lift_coefficients.
3. Fit the trim curve with trim_curve_fit (slope, intercept, R^2).
4. Locate the stick fixed neutral point and static margin with
   stick_fixed_neutral_point; flag an unstable slope.
5. With hinge moment data, find the stick free neutral point with
   stick_free_neutral_point.
6. Assess the elevator angle per g with elevator_angle_per_g.
7. Chain everything with static_stability_report for the final
   stability verdict.

## Pitfalls

- Fitting elevator angle versus speed directly and reading the sign:
  convert to lift coefficient first; the slope convention
  b = d(delta_e)/dCL only holds after the conversion.
- Mixing units: Cm_delta_e and the hinge derivatives are per radian
  while the measured elevator angle is in degrees; the module
  converts with (pi/180).
- Forgetting the stick free shift: the free elevator neutral point is
  forward of the stick fixed value, so the stick free static margin
  is smaller.
- Treating the practice bands as regulation text: the numbers here
  are typical flight test practice; the certification criteria in the
  cited standards take precedence.

## Behavior contract (gate 3)

The static stability logic is exercised by the gate 3 contract test:
scripts/test_static_stability_flight_test.py against
scripts/static_stability_flight_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_static_stability_flight_test.py

## Compliance

- The trim curve reduction, the neutral point relations, and the
  elevator angle per g are common flight test methodology,
  paraphrased here. FAR-25 and CS-25 are cited as reference only for
  the stability demonstration context; no proprietary or copyrighted
  text is reproduced.
- compliance: STANDARDS-REF, gated: false.
