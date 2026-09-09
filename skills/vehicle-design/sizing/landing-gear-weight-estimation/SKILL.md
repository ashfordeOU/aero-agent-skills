---
name: landing-gear-weight-estimation
description: "Use when you must predict the landing gear group weight at the class-II level for the weight statement: evaluate the statistical main-gear-group-weight regression on the design landing weight, the ultimate landing load factor and the main gear strut length with the wheel, strut and stall speed terms, evaluate the nose-gear-group-weight regression on the design landing weight, the ultimate landing load factor and the nose gear strut length with the nose wheel count, with the limit landing load factor scaled to ultimate by the 1.5 safety factor, and sum the two group masses into the landing gear group total. Produces the main and nose gear group masses in kg, the gear group total, and its fraction of the design landing weight for the weight statement. Trigger: landing gear group weight estimation, gear weight regression, main gear group weight, nose gear group weight, class ii gear weight buildup."
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
  tags: [landing-gear-weight-estimation, landing-gear-group-weight, main-gear-group-weight, nose-gear-group-weight, gear-group-weight-regression, class-ii-gear-weight-buildup]
  version: 0.1.0
  author: AeroSkills
---

# Landing Gear Weight Estimation (vehicle-design/sizing/landing-gear-weight-estimation)

Use when you must predict the landing gear group weight at the
class-II level for the weight statement: converting the design landing
weight, the ultimate landing load factor and the gear geometry into
the main and nose gear group masses through two published statistical
power-law regressions, then summing them into the landing gear group
total. This leaf implements the class-II landing gear weight
prediction of the weight estimation chapter of Raymer, Aircraft
Design: A Conceptual Approach, paraphrased in this leaf's own notation
(the books are proprietary-sold; summary-only), in pure Python, stdlib
only. It pairs with vehicle-design/sizing/landing-gear-retraction-sizing,
which takes the gear weight this leaf produces as a given input to the
retraction moment, and with vehicle-design/mass-properties/mass-budget,
which collects the gear group mass this leaf produces alongside the
other subsystem mass estimates for the rollup.

## Domain quick reference

- Ultimate landing load factor: N_ult = 1.5 * n_land_limit, the FAR-25.303
  factor of safety between the design limit landing load factor and the
  ultimate value used in both regressions.
- Main gear group (lb, strut length in, stall speed knots): W_main =
  0.0106 * W_l^0.888 * N_ult^0.25 * L_m^0.4 * N_mw^0.321 * N_mss^-0.5 *
  V_s^0.1, with W_l the design landing weight, L_m the extended main
  strut length, N_mw the total main wheel count, N_mss the main shock
  strut count and V_s the stall speed in knots.
- Nose gear group (lb, strut length in): W_nose = 0.032 * W_l^0.646 *
  N_ult^0.2 * L_n^0.5 * N_nw^0.45, with L_n the extended nose strut
  length and N_nw the total nose wheel count.
- Unit boundary: inputs and outputs are SI (kg, m, dimensionless
  counts) with the stall speed kept in knots as published; the
  regressions run in the published lb / in closed forms and convert at
  the boundary with fixed constants (1 kg = 1/0.45359237 lb, 1 m =
  1/0.0254 in).
- The K_mp (non-kneeling gear) and K_np (non-reciprocating
  installation) factors are 1.0 in this transport form and are folded
  into the leading constants 0.0106 and 0.032; kneeling-gear and
  reciprocating-engine variants are outside this leaf's claim.
- Both landing weight exponents (0.888 main, 0.646 nose) are below 1,
  so the gear group total scales slower than the design landing weight
  and the gear group fraction of the landing weight falls as the
  design grows. The main shock strut exponent is negative (-0.5), so
  spreading the main gear load over more shock struts lowers the main
  gear group estimate.
- Torenbeek, Synthesis of Subsonic Airplane Design, places the landing
  gear group near 3.8 to 4.5 percent of gross weight for aircraft above
  10000 lb, the magnitude cross-check band for the group total.

## Workflow

1. Fix the design point: the design landing weight in kg, the design
   limit landing load factor (scaled internally to ultimate by the 1.5
   safety factor), and the gear geometry (main and nose strut lengths,
   wheel counts, main shock strut count and stall speed).
2. Evaluate main_gear_group_weight on the design landing weight, the
   limit load factor, the main strut length, the main wheel count, the
   main shock strut count and the stall speed.
3. Evaluate nose_gear_group_weight on the design landing weight, the
   limit load factor, the nose strut length and the nose wheel count.
4. Sum the two group masses with landing_gear_group_total, and take
   gear_group_fraction of that total against the design landing weight
   and against MTOW for the weight statement fraction check.
5. Sanity-check the class-II band and the exact-power identities: each
   group mass scales by 2 raised to its regressor's published exponent
   when that regressor doubles with all else fixed, and the gear group
   fraction of the design landing weight falls as the landing weight
   grows.
6. Reject non-physical inputs with ValueError, and confirm the
   deterministic checks with the contract test
   scripts/test_landing_gear_weight_estimation.py.

## Worked example

180-seat narrowbody transport: design landing weight 66000.0 kg, limit
landing load factor 3.0 (N_ult = 4.5), main gear extended strut length
2.30 m with 4 main wheels on 2 shock struts at stall speed 115.0 kts,
nose gear extended strut length 1.40 m with 2 nose wheels, MTOW
79000.0 kg.

- main_gear_group_weight gives 2893.904950 kg, nose_gear_group_weight
  gives 430.316692 kg, and landing_gear_group_total gives
  3324.221642 kg.
- Fractions: 0.050367 of the 66000.0 kg design landing weight, 0.042079
  of the 79000.0 kg MTOW (inside the Torenbeek 0.038 to 0.045
  gross-weight band), and the nose gear group is 0.129449 of the group
  total.
- The main gear group is 28.380 kN as a force, 14.190 kN per shock
  strut leg, on the order of the 14000 N main-gear leg weight that the
  landing-gear-retraction-sizing worked example fixes as a given input,
  confirming this leaf produces the input that leaf consumes.
- Design landing weight power law: doubling to 132000.0 kg scales the
  main group by 1.850608856 (2^0.888) and the nose group by 1.564823563
  (2^0.646), and the gear group fraction of the design landing weight
  falls from 0.050367 to 0.045673.
- Load factor power law: doubling n_land_limit to 6.0 (N_ult 9.0)
  scales the main group by 1.189207115 (2^0.25) and the nose group by
  1.148698355 (2^0.2).
- Geometry power laws: doubling the main strut length scales the main
  group by 1.319507911 (2^0.4), the nose strut length scales the nose
  group by 1.414213562 (2^0.5), the main wheel count scales the main
  group by 1.249196126 (2^0.321), the nose wheel count scales the nose
  group by 1.366040257 (2^0.45), the main shock strut count scales the
  main group by 0.707106781 (2^-0.5, a fall), and the stall speed
  scales the main group by 1.071773463 (2^0.1).

## Verification

- Confirm main_gear_group_weight(66000.0, 3.0, 2.30, 4, 2, 115.0)
  returns 2893.904950 kg and nose_gear_group_weight(66000.0, 3.0, 1.40,
  2) returns 430.316692 kg, both within 1e-6 relative.
- Confirm landing_gear_group_total of the two returns 3324.221642 kg,
  its fraction of the design landing weight is 0.050367 and of MTOW is
  0.042079, inside the class-II expectation band.
- Confirm every exact-power identity in the Worked example holds within
  1e-9 relative when its regressor doubles.
- Confirm every non-positive design landing weight, limit landing load
  factor, main or nose strut length or stall speed, and every wheel or
  shock strut count below 1, raises ValueError with the documented
  message; confirm landing_gear_group_total raises ValueError for a
  negative or non-number group mass.
- Run the contract test offline: python3
  scripts/test_landing_gear_weight_estimation.py (38 tests,
  deterministic, no randomness).

## Related leaves

- vehicle-design/sizing/landing-gear-retraction-sizing: consumes the
  gear weight this leaf produces as the given input to the retraction
  moment.
- vehicle-design/sizing/component-weight-estimation: the wave-47
  sibling that predicts the four airframe structural group masses
  (wing, horizontal tail, vertical tail, fuselage); this leaf covers
  the landing gear group instead.
- vehicle-design/mass-properties/mass-budget: collects the gear group
  mass this leaf produces alongside the other subsystem mass estimates
  for the rollup.
- vehicle-design/sizing/weight-estimation: takes component weights
  (including the gear group total this leaf produces) as given inputs
  for the class-I/class-II weight and balance moments and CG.

## Pitfalls

- Using the limit landing load factor directly in the regressions: both
  power laws take the ULTIMATE value N_ult = 1.5 * n_land_limit, so
  feeding the limit value (3.0 in the worked example) instead of the
  ultimate (4.5) understates both group masses.
- Sizing the regressor on MTOW: the weight regressor is the design
  LANDING weight, not the takeoff weight; the worked example's
  66000.0 kg landing weight is 0.835 of the 79000.0 kg MTOW, and
  feeding MTOW in its place overstates both group masses.
- Dropping the shock strut term: the main gear group exponent on the
  shock strut count is negative (-0.5), so a single-strut assumption
  when the design actually spreads the load over 2 struts overstates
  the main gear group by 2^0.5 = 1.414.
- Mixing unit systems mid-call: the regressions are the published lb /
  in closed forms; feeding meters where inches are expected (or
  omitting the kg-to-lb conversion) breaks the published constants
  silently rather than raising an error.
- Reading the gear group total as a strut load or a retraction demand:
  this leaf produces the class-II MASS estimate only; static strut
  loads, retraction moments, tire loads and gear heights are all owned
  by sibling leaves that take this leaf's output (or a given gear
  weight) as their input.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_landing_gear_weight_estimation.py

The test covers the worked example (main and nose gear group masses
and the landing gear group total within 1e-6 relative), the class-II
physical-sanity bands (positive masses, main above nose, total below
the design landing weight, fraction bands of the design landing weight
and MTOW), every exact-power identity within 1e-9 relative, the
sublinear scaling and monotonicity in the design landing weight, the
retraction-sibling per-leg cross-check, ValueError rejection of every
non-physical input with the documented message, and determinism across
repeated calls (38 tests, deterministic, no randomness).

## Compliance

Standards referenced, not reproduced: 14 CFR Part 25 and CS-25 are
reference-only per standards-map.yaml; the class-II statistical weight
method above is paraphrased engineering methodology, summary-only, no
verbatim text from the source treatments. compliance: STANDARDS-REF,
gated: false.
