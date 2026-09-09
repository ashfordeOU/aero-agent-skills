---
name: fuel-system-weight-estimation
description: "Use when you must predict the fuel system group weight at the class-II level for the weight statement: evaluate the statistical fuel system weight regression of the transport integral-tank fuel system on the total fuel weight and the tank arrangement, the fixed 80 lb count allowance per tank and engine unit plus the 15 lb volume term scaling with the square root of the tank count and the cube root of the fuel quantity at the published fuel specific weight, and sum the terms into the fuel system group mass. Produces the fuel system group mass in kg for the tanks, sealing, pumps, plumbing and distribution hardware, and its fraction of the total fuel weight for the weight statement and the mass budget rollup. Trigger: fuel system weight estimation, fuel system group weight, fuel system weight regression, class ii fuel system weight buildup, tank group weight estimation."
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
  tags: [fuel-system-weight-estimation, fuel-system-group-weight, fuel-system-weight-regression, class-ii-fuel-system-weight-buildup, tank-group-weight-estimation]
  version: 0.1.0
  author: AeroSkills
---

# Fuel System Weight Estimation (vehicle-design/sizing/fuel-system-weight-estimation)

Use when you must predict the fuel system group weight at the class-II
level for the weight statement: converting the total fuel weight and
the tank arrangement into the fuel system group mass, the hardware
mass of the tanks, sealing, pumps, collector tanks, plumbing,
distribution and filling equipment, through a published statistical
power-law regression. This leaf implements the class-II fuel system
weight prediction of the fuel system weight estimation treatment of
Roskam, Airplane Design Part V: Component Weight Estimation (the
Torenbeek method for commercial transport airplanes with integral fuel
tanks), paraphrased in this leaf's own notation (the books are
proprietary-sold; summary-only), in pure Python, stdlib only. It pairs
with vehicle-design/sizing/fuel-tank-sizing, which converts the fuel
mass to the tank volume this leaf's tank arrangement builds on, and
with vehicle-design/mass-properties/mass-budget, which collects the
fuel system group mass this leaf produces alongside the other
subsystem mass estimates for the rollup.

## Domain quick reference

- Fixed count allowance term (lb): W_a = 80 * (N_t + N_e - 1), with N_t
  the number of separate fuel tanks and N_e the number of engines.
  Fuel independent; linear in the tank and engine count sum.
- Volume-scaled tankage term (lb): W_v = 15 * (N_t)^0.5 * V^(1/3), with
  V = W_F / 6.55 the fuel quantity in US gallons at the published fuel
  specific weight and W_F the total fuel weight in lb. Sublinear in
  both the tank count (exponent 0.5) and the fuel quantity (exponent
  1/3).
- Fuel system group: W_fs = W_a + W_v, the sum of the two published
  terms of the source equation.
- Fuel specific weight: 6.55 lb per US gallon, the published JP-4
  jet-fuel value of the source; modern Jet A sits within about 2
  percent of it, and the fixed constant keeps every published
  coefficient visible.
- Unit boundary: inputs and outputs are SI (kg, dimensionless counts);
  the regression runs in the published lb / US gallon closed form and
  converts at the boundary with fixed constants (1 kg = 1/0.45359237
  lb).
- The group total scales strictly sublinearly in the fuel weight: the
  allowance is fuel independent and the tankage term carries the
  one-third exponent, so the fuel system group fraction of the fuel
  weight falls as the fuel weight grows.
- The public NASA comparison of conceptual design weight methods
  (Horvath and Wells) reports the FLOPS and actual Boeing 737-200 fuel
  system (tanks and plumbing) weights near 553 lb and 575 lb, about
  0.02 of that airplane's fuel weight and about 0.005 of its gross
  weight, the class-II magnitude cross-check band.

## Workflow

1. Fix the design point: the total fuel weight in kg (the design total
   fuel weight, mission fuel including reserves), the number of
   separate fuel tanks, and the number of engines.
2. Evaluate fuel_system_count_allowance_kg on the tank and engine
   counts, the fixed count allowance term.
3. Evaluate fuel_system_volume_term_kg on the total fuel weight and
   the tank count, the volume-scaled tankage term.
4. Sum the two terms with fuel_system_group_weight, and take
   fuel_system_group_fraction of that total against the total fuel
   weight and against MTOW for the weight statement fraction check.
5. Sanity-check the class-II band and the exact-power identities: the
   volume term scales by 2^(1/3) when the fuel weight doubles and by
   2^0.5 when the tank count doubles, all else fixed, and the fuel
   system group fraction of the fuel weight falls as the fuel weight
   grows.
6. Reject non-physical inputs with ValueError, and confirm the
   deterministic checks with the contract test
   scripts/test_fuel_system_weight_estimation.py.

## Worked example

180-seat narrowbody transport: total fuel weight 22000.0 kg (design
total fuel weight, mission fuel including reserves), 3 separate
integral fuel tanks (left wing, right wing and center wing), 2
engines, MTOW 79000.0 kg for the weight-statement fractions. The fuel
quantity at the published specific weight is 7404.839341 US gallons.

- fuel_system_count_allowance_kg(3, 2) gives 145.149558400 kg (the 320
  lb allowance at 4 count units), fuel_system_volume_term_kg(22000.0,
  3) gives 229.697449925 kg, and fuel_system_group_weight(22000.0, 3,
  2) gives 374.847008325 kg, the exact sum of the two terms.
- Fractions: 0.017038500 of the 22000.0 kg total fuel weight,
  0.004744899 of the 79000.0 kg MTOW. The group mass sits inside the
  class-II band (the NASA weight-methods comparison FLOPS and actual
  Boeing 737-200 tanks-and-plumbing weights sit near 0.02 of the fuel
  weight and near 0.005 of gross weight), and the MTOW fraction sits
  far below the class-I transport empty-weight band lower bound 0.42
  that the weight-estimation sibling checks.
- Fuel volume power law: recomputing fuel_system_volume_term_kg at
  44000.0 kg gives 289.400652267 kg, a ratio of 1.259921049895 against
  its value at 22000.0 kg, matching 2^(1/3).
- Tank count power law: recomputing fuel_system_volume_term_kg with 6
  tanks at the same fuel gives 324.841248926 kg, a ratio of
  1.414213562373 against the 3 tank value, matching 2^0.5.
- Count allowance additivity: one extra tank at 2 engines adds
  36.287389600 kg and one extra engine at 3 tanks adds 36.287389600
  kg, each exactly the 80.0 lb allowance unit, and the allowance is
  fuel independent.
- Sublinear fuel scaling: fuel_system_group_weight at 44000.0 kg gives
  434.550210667 kg, a ratio of 1.159273519641 against the 22000.0 kg
  value, below 2^(1/3) = 1.259921049895, and the fuel system fraction
  of the fuel weight falls from 0.017038500 at 22000.0 kg to
  0.009876141 at 44000.0 kg.
- Monotonicity: the group at 1.01 times the fuel (22220.0 kg) gives
  375.610128382 kg and the group at 4 tanks gives 446.668717092 kg,
  both strictly above the worked 374.847008325 kg.

## Verification

- Confirm fuel_system_count_allowance_kg(3, 2) returns 145.149558400
  kg, fuel_system_volume_term_kg(22000.0, 3) returns 229.697449925 kg,
  and fuel_system_group_weight(22000.0, 3, 2) returns 374.847008325
  kg, all within 1e-6 relative.
- Confirm the group fractions are 0.017038500 of the total fuel weight
  and 0.004744899 of MTOW, inside the class-II expectation band.
- Confirm every exact-power identity in the Worked example holds
  within 1e-9 relative when its regressor doubles, and the count
  allowance additivity holds within 1e-9 relative.
- Confirm the group mass equals the count allowance plus the volume
  term within 1e-12 relative.
- Confirm every non-positive or non-number total fuel weight, every
  tank or engine count below 1 or fractional, and a tank count below
  the engine count, raises ValueError with the documented message.
- Run the contract test offline: python3
  scripts/test_fuel_system_weight_estimation.py (32 tests,
  deterministic, no randomness).

## Related leaves

- vehicle-design/sizing/fuel-tank-sizing: converts the fuel mass to
  the fuel volume and the required tank volume; this leaf takes the
  resulting tank arrangement as an input and produces the tank
  hardware group mass instead of a volume.
- vehicle-design/sizing/fuel-feed-system-sizing: feed line hydraulics,
  Reynolds number, pressure loss, NPSH and boost pump power between
  the tank and the engine; a separate hydraulic sizing output, never a
  group mass.
- vehicle-design/sizing/component-weight-estimation: the wave-47
  sibling that predicts the four airframe structural group masses
  (wing, horizontal tail, vertical tail, fuselage); the fuel system
  group is deliberately outside that four-group claim, and this leaf
  produces the fuel system line of the weight statement instead.
- vehicle-design/mass-properties/mass-budget: collects the fuel system
  group mass this leaf produces alongside the other subsystem mass
  estimates for the rollup.
- vehicle-design/sizing/weight-estimation: takes component weights
  (including the fuel system group total this leaf produces) as given
  inputs for the class-I/class-II weight and balance moments and CG.

## Pitfalls

- Using the mission fuel weight instead of the design total fuel
  weight: the regressor W_F is the design total fuel weight including
  reserves per the source convention; a partial or block fuel value
  understates both the volume term and the group total.
- Sizing the volume term on the wrong specific weight: the published
  form fixes 6.55 lb per US gallon (JP-4); the aviation gasoline value
  5.87 is outside the claim and would inflate the fuel quantity and
  the volume term.
- Feeding a tank count below the engine count: the integral-tank
  transport arrangement of the source feeds every engine from its own
  tank group, so a tank count below the engine count is outside the
  arrangement and raises ValueError rather than a silently wrong
  answer.
- Reading the fuel system group mass as a fuel volume, a tank
  capacity, a feed flow, a jettison rate, an installed engine weight
  or any four-airframe-group weight: this leaf produces the class-II
  hardware MASS estimate only, never the outputs the fuel-chain and
  component-weight-estimation siblings own.
- Assuming linear scaling with fuel weight: the tankage term carries
  the one-third exponent, so doubling the fuel weight scales the group
  by only 1.159273519641, not 2.0, and the fuel system fraction of the
  fuel weight falls as the design fuel weight grows.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fuel_system_weight_estimation.py

The test covers the worked example (count allowance, volume term and
group weight within 1e-6 relative, and the group fractions of the
total fuel weight and MTOW), the class-II physical-sanity bands
(positive mass, group below the total fuel weight and MTOW, fraction
bands, and the MTOW fraction far below the class-I empty-weight band),
the exact-power identities for the fuel weight and tank count
regressors, the count allowance additivity and fuel independence, the
group additivity identity, the sublinear fuel scaling and fraction
fall, monotonicity in the fuel weight and the tank count, ValueError
rejection of every non-physical input with the documented message, and
determinism across repeated calls (32 tests, deterministic, no
randomness).

## Compliance

Standards referenced, not reproduced: 14 CFR Part 25 and CS-25 are
reference-only per standards-map.yaml; the class-II statistical fuel
system weight method above is paraphrased engineering methodology,
summary-only, no verbatim text from the source treatments. compliance:
STANDARDS-REF, gated: false.
