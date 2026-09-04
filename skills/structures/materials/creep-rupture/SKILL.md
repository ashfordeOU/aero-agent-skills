---
name: creep-rupture
description: "Use when you must assess the elevated-temperature creep and stress rupture behavior of an aerospace metallic part: compute the steady-state creep strain rate with the Norton power law eps_dot = A * sigma^n * exp(-Q/(R*T)) from the stress and the temperature, estimate the rupture life in hours with the Larson-Miller parameter from the stress-LMP master curve, apply the Monkman-Grant relation between the minimum creep rate and the rupture life, accumulate the creep strain over the service time, and check the time to 1 percent creep strain and the rupture life against the required design life with the margin verdict. Produces the creep rate, the rupture life, the accumulated creep strain, and the governing margin for the hot-section component. Trigger: creep-rupture, norton-creep-law, steady-state-creep-rate, larson-miller-parameter, monkman-grant, rupture-life, stress-rupture, accumulated-creep-strain, time-to-one-percent-creep, elevated-temperature."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: materials
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: materials
  tags: [creep-rupture, norton-creep-law, steady-state-creep-rate, larson-miller-parameter, monkman-grant, rupture-life, stress-rupture, accumulated-creep-strain, time-to-one-percent-creep, elevated-temperature]
  version: 0.1.0
  author: Aero Agent Skills
---

# Creep and Stress Rupture (structures/materials/creep-rupture)

Use when the task is the time-dependent creep and stress rupture life of
an aerospace metallic part at elevated temperature: the steady-state
creep strain rate from the Norton power law, the rupture life from the
Larson-Miller parameter, the Monkman-Grant cross-check from the minimum
creep rate, the creep strain accumulated over the service time, and the
design-life margin check. This leaf implements the classic parametric
methods in pure Python, stdlib only. It pairs with
structures/materials/ramberg-osgood for the room-temperature
elastic-plastic curve, structures/materials/fracture-toughness for the
crack-driven failure mode, structures/materials/material-selection for
the temperature limits in the alloy trade, and structures/thermal-
structures/thermal-stress-analysis for the load side of the same
elevated-temperature environment. This leaf does NOT cover cyclic
endurance (the structures/fatigue pack owns cyclic life methods),
constrained-expansion thermal stress, or statistically based tensile
design values (structures/materials/mmpsd-allowables).

## Domain quick reference

- Norton steady-state creep rate: eps_dot_c = A * sigma^n *
  exp(-Q / (R * T)), with A in 1/s per Pa^n, n the stress exponent, Q
  the activation energy in J/mol, R = 8.314 J/mol/K and T in K. The
  default module material is a representative nickel superalloy
  (Inconel-718 class) with reference-only typicals A = 2.0e-47,
  n = 7.0, Q = 360000 J/mol; any of A, n, Q and the LMP/MG constants
  can be overridden with a dict.
- Larson-Miller parameter: LMP = T * (C + log10(t_r)), with t_r the
  rupture life in hours, T in K, C a material constant (about 20). The
  stress-LMP master curve is taken linear in log10 stress:
  LMP = lm_a - lm_b * log10(sigma_pa / 1e6), lm_a = 35552,
  lm_b = 6000 for the default alloy.
- Rupture life from the LMP: t_r = 10 ** (LMP / T - C), hours.
- Monkman-Grant: log10(t_r) + m * log10(eps_dot_min) = C_mg with the
  creep rate in 1/h (m = 1.0, C_mg = -1.645 default); gives a rupture
  life from the minimum creep rate that cross-checks the LMP estimate.
- Accumulated creep strain: eps_c(t) = eps_dot_c * t over the service
  time (steady-state only; primary creep is neglected in this leaf, a
  documented conservative assumption for the design check).
- Time to a target creep strain: t = target / eps_dot_c; the 1 percent
  creep design point is t_1pct = 0.01 / eps_dot_c.
- Margins against the required life t_req: margin_rupture =
  t_r / t_req - 1 and margin_creep = t_1pct / t_req - 1; the lower
  margin governs and the verdict is PASS when it is >= 0.
- Units: stress in Pa, temperature in K, time in seconds (rupture
  lives reported in hours where noted). All functions raise ValueError
  on non-positive stress, temperature, time, target strain or creep
  rate, a negative stress exponent, or an unknown material name.

## Workflow

1. Fix the operating point: the sustained stress sigma in Pa (convert
   MPa by multiplying by 1e6) and the metal temperature T in K
   (Celsius plus 273.15).
2. Compute the steady-state creep rate with norton_creep_rate(sigma,
   temp_k, material); pass a registered material name or a dict of
   constant overrides on top of the default alloy.
3. Get the Larson-Miller parameter at the stress with
   larson_miller_parameter(sigma, material) and the rupture life with
   rupture_life_hours(sigma, temp_k, material); the raw conversion
   rupture_life_from_lmp(lmp, temp_k, c_const) exposes the formula.
4. Cross-check with the Monkman-Grant route: monkman_grant_life(
   eps_dot_min, material) from the Norton rate; the two rupture lives
   should agree within the scatter band of the material data.
5. Accumulate the damage over the service time with
   creep_strain_accumulated(eps_dot, time_s), and read the 1 percent
   design point from time_to_creep_strain(0.01, eps_dot).
6. Run the design check with creep_margin(time_required_s, sigma,
   temp_k, material): it returns the rupture life, the time to 1
   percent strain, both margins, the governing mode and the PASS/FAIL
   verdict for the required life.
7. Confirm the deterministic checks with the contract test
   scripts/test_creep_rupture.py.

## Worked example

A turbine disk rim material at 300 MPa and 600 C (873.15 K), 1000 h
required life, default alloy constants:

- Norton creep rate: eps_dot = 2.0e-47 * (3.0e8)^7 *
  exp(-360000 / (8.314 * 873.15)) = 1.2698e-9 1/s.
- Larson-Miller parameter: LMP = 35552 - 6000 * log10(300) =
  20689.27.
- Rupture life (LMP route): t_r = 10 ** (20689.27 / 873.15 - 20) =
  4954.3 h, well above the 1000 h requirement.
- Rupture life (Monkman-Grant route): with eps_dot per hour =
  4.5714e-6, log10(t_r) = -1.645 - log10(4.5714e-6) = 3.695, so
  t_r = 4954.0 h, matching the LMP estimate within 0.01 percent.
- Time to 1 percent creep strain: t_1pct = 0.01 / 1.2698e-9 =
  7875105.5 s = 2187.5 h.
- Accumulated strain over the 1000 h service time: 1.2698e-9 *
  3600000 = 0.00457, below the 1 percent design point.
- Margin check: margin_rupture = 4954.3 / 1000 - 1 = 3.954 and
  margin_creep = 2187.5 / 1000 - 1 = 1.188. The lower margin is the
  creep margin, so creep governs the design and the verdict is PASS.
- Sensitivity: raise the temperature to 650 C (923.15 K) at the same
  stress and the rupture life collapses to 258.0 h while t_1pct falls
  to 149.1 h; against the 1000 h requirement both margins go negative
  and the verdict is FAIL, showing why the creep check lives at the
  hot operating point.


## Pitfalls

- Forgetting creep is time at temperature: the Norton rate is
  exponentially sensitive to T (the rupture life collapses from
  4954 h at 600 C to 258 h at 650 C in the worked example), so a
  room-temperature check or a small temperature slip misses the
  whole failure mode.
- Neglecting the primary-creep assumption: the accumulated strain
  eps_c = eps_dot * t is steady-state only; primary creep is
  neglected by design as a conservative assumption, and the margin
  should be read with that in mind.
- Checking only one margin: creep_margin returns BOTH the rupture
  margin (3.954) and the 1-percent-strain margin (1.188) in the
  worked example, and the LOWER one governs - the time to 1 percent
  strain can gate before rupture.
- Trusting one rupture-life route: the LMP and Monkman-Grant
  estimates should agree within the material scatter band (they
  match within 0.01 percent in the worked example); a large
  discrepancy signals a bad input or a material outside the master
  curve.
- Mixing units in the input chain: stress enters in Pa (convert MPa
  by 1e6), temperature in K (Celsius plus 273.15), time in seconds
  for the margin check while rupture lives come back in hours; a
  seconds-versus-hours slip misreads the life by 3600x.
- Treating the module material as an alloy database: the Inconel-718
  class constants are reference-only typicals and any of A, n, Q and
  the LMP/MG constants can be overridden with a dict; quoting the
  defaults for another alloy is a material-data error.
## Verification

- Confirm norton_creep_rate(3.0e8, 873.15) returns 1.2698e-9 1/s and
  that the rate rises monotonically over 5 stress points and with
  temperature.
- Confirm rupture_life_hours(3.0e8, 873.15) returns 4954.3 h, that the
  life falls monotonically over 5 stress points and as the temperature
  rises, and that monkman_grant_life at the Norton rate agrees with the
  LMP life within 0.1 percent.
- Confirm creep_margin(3600000.0, 3.0e8, 873.15) returns margins 3.954
  and 1.188 with governing "creep" and verdict "PASS", and that the
  20000 h and 650 C cases return "FAIL".
- Confirm the round trip: rupture_life_from_lmp of the module LMP
  recovers the rupture life, and time_to_creep_strain scales inversely
  with the creep rate.
- Confirm every non-positive stress, temperature, time, target strain
  and creep rate, every negative stress exponent, and every unknown
  material name raises ValueError.
- Run the contract test offline: python3
  scripts/test_creep_rupture.py (34 tests, deterministic).

## Related leaves

- structures/materials/ramberg-osgood: the room-temperature
  elastic-plastic stress-strain curve beneath the creep regime.
- structures/materials/fracture-toughness: the crack-driven failure
  mode that competes with creep rupture in hot-section parts.
- structures/materials/material-selection: temperature limits and alloy
  family screening before the creep check.
- structures/thermal-structures/thermal-stress-analysis: the
  constrained-expansion load side of the same elevated-temperature
  environment (owned by that leaf, not here).
- structures/fatigue/stress-life-curve and structures/fatigue/strain-
  life-fatigue: cyclic life methods, the non-creep route for the same
  part.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_creep_rupture.py

The test covers the worked-example anchors (Norton rate 1.2698e-9 1/s,
LMP 20689.27, rupture life 4954.3 h, time to 1 percent strain 2187.5 h,
1000 h margin verdict PASS), the monotonicity of the creep rate with
stress and temperature and of the rupture life with stress and
temperature, the Monkman-Grant vs LMP cross-check, the accumulated
strain and time-to-strain scalings, the margin verdicts at long and hot
operating points, material dict overrides, and ValueError rejection of
non-physical inputs and unknown materials.

## Compliance

- Standards referenced, not reproduced: MMPDS documents creep and
  creep-rupture design practice for metallic airframe materials; FAR-25
  frames the elevated-temperature part and its strength demonstration.
  The equations above are standard engineering methodology,
  summary-only per standards-map.yaml, and the material constants are
  reference-only typicals, not a reproduced data table.
- compliance: STANDARDS-REF, gated: false.
