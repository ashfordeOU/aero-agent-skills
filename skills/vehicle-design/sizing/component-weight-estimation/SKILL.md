---
name: component-weight-estimation
description: "Use when you must predict the airframe structural group weights at the class-II level from geometry and design loading: evaluate the statistical wing-group-weight regression on the planform area, aspect ratio, sweep, thickness ratio and design load factor, the horizontal-tail-group-weight and vertical-tail-group-weight regressions on the tail planforms, and the fuselage-group-weight regression on the wetted area, fineness ratio and design gross weight, with the limit load factor scaled to ultimate by the 1.5 safety factor and the pressurization penalty added when a pressurized volume and differential are supplied. Produces the four group masses in kg, the airframe group total, and the group fractions of MTOW that feed the weight statement. Trigger: component weight estimation, group weight equation, wing group weight, fuselage group weight, horizontal tail weight, vertical tail weight, statistical weight prediction, class ii weight buildup."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [component-weight-estimation, group-weight-equation, wing-group-weight, fuselage-group-weight, horizontal-tail-group-weight, vertical-tail-group-weight, statistical-weight-prediction, class-ii-weight-buildup]
  version: 0.1.0
  author: AeroSkills
---

# Component Weight Estimation (vehicle-design/sizing/component-weight-estimation)

Use when the task is predicting the four airframe structural group
masses at the class-II level from geometry and design loading: the
wing group, the horizontal tail group, the vertical tail group and the
fuselage group, each from a published closed-form statistical
regression on its planform or body dimensions, sweep, thickness ratio,
dynamic pressure, design load factor and design gross weight. This
leaf implements the class-II statistical group-weight prediction
method of the weight estimation chapter of Raymer, Aircraft Design: A
Conceptual Approach, paraphrased in this leaf's own notation
(summary-only, reference-only). It pairs with
vehicle-design/sizing/wing-planform-sizing, tail-sizing and
fuselage-sizing for the geometry inputs, vehicle-design/sizing/
fuel-tank-sizing for the in-wing fuel mass, and hands its group masses
downstream to vehicle-design/sizing/weight-estimation and
vehicle-design/mass-properties/mass-budget as given component inputs.

## Domain quick reference

- Ultimate load factor: N_ult = 1.5 * nz_limit, the FAR-25.303 factor
  of safety between the design limit maneuvering load factor and the
  ultimate value used in every regression.
- Wing group (lb): W_w = 0.036 * S_w^0.758 * W_fw^0.0035 *
  (A_w / cos^2 L_w)^0.6 * q^0.006 * lam_w^0.04 *
  (100 * tc_w / cos L_w)^-0.3 * (N_ult * W0)^0.49.
- Horizontal tail group (lb): W_ht = 0.016 * (N_ult * W0)^0.414 *
  (A_ht / cos^2 L_ht)^0.168 * q^0.043 * S_ht^0.896 *
  (100 * tc_ht / cos L_ht)^-0.12 * lam_ht^0.02.
- Vertical tail group (lb): W_vt = 0.073 * (1 + 0.2 * H_t) *
  (N_ult * W0)^0.376 * q^0.122 * S_vt^0.873 *
  (100 * tc_vt / cos L_vt)^-0.49 * A_vt^0.357 *
  (lam_vt / cos^2 L_vt)^0.039, with H_t the T-tail location factor
  (0.0 fuselage-mounted, 1.0 T-tail).
- Fuselage group (lb): W_fus = 0.052 * S_f^1.086 * (N_ult * W0)^0.177 *
  (L_f / D_f)^-0.072 * q^0.241, plus the additive pressurization
  penalty W_press = 11.9 * (V_p * dp)^0.271 in lb when a pressurized
  volume and a pressure differential are both supplied.
- Every regressor is SI in, kg out; the regressions themselves run in
  the published lb / ft^2 / psf closed forms and convert at the
  boundary with fixed unit constants (KG_TO_LB, M_TO_FT, PA_TO_PSF,
  PA_TO_PSI), so every published coefficient stays visible.
- The four regressions are sublinear in (N_ult * W0), every exponent
  below 0.5, so the airframe group total scales slower than MTOW as
  the design grows.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context that
  the ultimate-over-limit factor of safety comes from.

## Workflow

1. Collect the design loading: MTOW in kg, the design limit
   maneuvering load factor, and the cruise dynamic pressure at the
   design point in Pa.
2. Evaluate the wing group with wing_group_weight on the wing
   planform area, aspect ratio, taper ratio, thickness to chord,
   quarter-chord sweep and the in-wing fuel mass.
3. Evaluate the horizontal tail group with
   horizontal_tail_group_weight and the vertical tail group with
   vertical_tail_group_weight on the respective tail planforms,
   passing the T-tail location factor for a T-tail configuration.
4. Evaluate the fuselage group with fuselage_group_weight on the
   wetted area, length and equivalent diameter, supplying the
   pressurized volume and cabin pressure differential together when
   the fuselage is pressurized.
5. Sum the four group masses into the airframe group total with
   airframe_group_total.
6. Divide each group mass and the total by MTOW to get the per-group
   and total fractions that feed the weight statement, and hand them
   downstream to the weight-and-balance and mass-budget consumers.
7. Confirm the deterministic checks with the contract test
   scripts/test_component_weight_estimation.py.

## Worked example

180-seat narrowbody transport, all inputs SI: MTOW 79000.0 kg, design
limit maneuvering load factor 2.5 (N_ult 3.75), cruise dynamic
pressure 12000.0 Pa.

- Wing: planform area 125.0 m^2, aspect ratio 10.0, taper ratio 0.25,
  thickness to chord 0.11, quarter-chord sweep 25.0 degrees, in-wing
  fuel 14000.0 kg. wing_group_weight gives 5835.319661 kg.
- Horizontal tail: area 32.0 m^2, aspect ratio 6.0, taper ratio 0.30,
  thickness to chord 0.09, sweep 30.0 degrees.
  horizontal_tail_group_weight gives 461.175701 kg.
- Vertical tail: area 26.0 m^2, aspect ratio 1.8, taper ratio 0.30,
  thickness to chord 0.12, sweep 35.0 degrees, fuselage-mounted
  (t_tail 0.0). vertical_tail_group_weight gives 438.062259 kg; the
  T-tail variant (t_tail 1.0) gives 525.674710 kg, exactly 1.2 times
  the fuselage-mounted value.
- Fuselage: wetted area 405.0 m^2, length 39.5 m, equivalent diameter
  3.9 m, pressurized volume 300.0 m^3, cabin pressure differential
  55158.0 Pa. fuselage_group_weight gives 7362.993775 kg; the
  unpressurized variant gives 7246.112306 kg, so the pressurization
  penalty is 116.881468 kg (about 1.6 percent of the fuselage group).
- airframe_group_total gives 14097.551395 kg. As fractions of the
  79000.0 kg MTOW: wing 0.073865, horizontal tail 0.005838, vertical
  tail 0.005545, fuselage 0.093202, four-group total 0.178450, which
  sits well below the class-I transport band lower bound of 0.42 that
  the weight-estimation sibling checks.
- Doubling the ultimate load factor scales the wing by 2^0.49 =
  1.404445, the horizontal tail by 2^0.414 = 1.332375, the vertical
  tail by 2^0.376 = 1.297739 and the unpressurized fuselage by
  2^0.177 = 1.130531. Doubling the dynamic pressure scales the same
  four groups by 2^0.006, 2^0.043, 2^0.122 and 2^0.241.

## Verification

- Confirm the worked-example values above to within 1e-6 relative for
  each group and the total.
- Confirm every group mass is positive, below the total, and the
  total is below MTOW; confirm the wing and fuselage fractions of
  MTOW fall in [0.05, 0.15], each empennage fraction in
  [0.004, 0.03], and the four-group fraction in [0.10, 0.30].
- Confirm the exact power-law identities: doubling the wing planform
  area, aspect ratio, taper ratio, in-wing fuel, tail areas, fuselage
  wetted area and fuselage length-to-diameter ratio scale each group
  by 2 raised to its published exponent, within 1e-9 relative.
- Confirm the T-tail factor is exactly 1.2 times the fuselage-mounted
  value within 1e-12 relative.
- Confirm the pressurization penalty is the difference between the
  pressurized and unpressurized fuselage mass, scales as 2^0.271 when
  the pressure differential doubles, and is unchanged when the load
  factor or dynamic pressure changes.
- Confirm ValueError rejection of a non-positive MTOW, limit load
  factor, dynamic pressure, planform area, aspect ratio, taper ratio,
  thickness to chord, sweep angle, wetted area, fuselage length and
  diameter, in-wing fuel mass, and negative t_tail or group mass; a
  thickness to chord at or above 1.0, a sweep at or above 90 degrees,
  and exactly one pressurization parameter supplied without the other.
- Run the contract test offline: python3
  scripts/test_component_weight_estimation.py (deterministic,
  identical outputs under both interpreters).

## Related leaves

- vehicle-design/sizing/wing-planform-sizing: the wing planform
  geometry that feeds the wing group regression.
- vehicle-design/sizing/tail-sizing: the tail planform geometry that
  feeds the horizontal and vertical tail group regressions.
- vehicle-design/sizing/fuselage-sizing: the fuselage dimensions that
  feed the fuselage group regression.
- vehicle-design/sizing/fuel-tank-sizing: the in-wing fuel mass input
  to the wing group regression.
- vehicle-design/sizing/weight-estimation: consumes the four group
  masses as given component weights for moments, CG and empty-weight
  fraction band checks.
- vehicle-design/mass-properties/mass-budget: rolls the group masses
  into the subsystem mass budget with growth allowance and margin.

## Pitfalls

- Feeding the limit load factor instead of the ultimate load factor
  into a regression: every group uses N_ult = 1.5 * nz_limit, so
  passing the limit value understates every group mass.
- Calling wing_group_weight with no in-wing fuel: the regression
  requires a positive fuel_in_wing_kg; a fuel-less wing is outside
  its domain and raises ValueError rather than silently zeroing the
  fuel term.
- Supplying only one of the pressurization parameters: the fuselage
  regression requires the pressurized volume and the pressure
  differential together, or neither; one without the other raises
  ValueError.
- Reading a group mass as a takeoff weight, an empty weight or a
  total aircraft mass: the four groups are the airframe structural
  share only, always below the class-I empty-weight fraction band
  that the weight-estimation sibling checks against given component
  weights.
- Treating the omitted tail-arm decorrelation factor as missing
  precision: the fuselage regression here omits the source table's
  small tail-arm term (below class-II resolution), changing the
  fuselage mass by under 1 percent against the full published form.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_component_weight_estimation.py

The test exercises workflow steps 2 through 6: the wing, horizontal
tail, vertical tail and fuselage group regressions at the worked
example, the airframe group total and its MTOW fractions, the T-tail
factor, the pressurization decomposition, the load-factor and dynamic
pressure power laws, the geometric power laws, the sweep penalty, and
ValueError rejection of every non-physical input enumerated above.

## Compliance

- Standards referenced, not reproduced: FAR-25 (14 CFR Part 25) is US
  government work (public domain) and CS-25 is a free EASA download;
  the class-II statistical group-weight method above is standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
