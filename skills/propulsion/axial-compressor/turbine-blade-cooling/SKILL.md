---
name: turbine-blade-cooling
description: "Use when you must analyze the cooling flow required to protect a gas turbine blade row: compute the cooling effectiveness from the hot gas total temperature, the allowable blade metal temperature and the coolant supply temperature, convert it into the required coolant-to-gas mass flow fraction with a simplified energy balance, check the fraction against the practical bleed limit, and estimate the achievable metal temperature when film cooling lifts the effectiveness. Produces the effectiveness, coolant fraction, bleed-limit verdict, metal temperature and margin that gate hot section cooling design in the FAR-33 engine context. Trigger: turbine blade cooling, cooling effectiveness, coolant flow fraction, film cooling, allowable metal temperature, coolant supply temperature, bleed limit, hot section cooling."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: axial-compressor
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: axial-compressor
  tags: [turbine-blade-cooling, cooling-effectiveness, coolant-flow-fraction, film-cooling, bleed-limit, allowable-metal-temperature, hot-section-cooling]
  version: 0.1.0
  author: Aero Agent Skills
---

# Turbine Blade Cooling (propulsion/axial-compressor/turbine-blade-cooling)

Use when the task is the heat-transfer side of a turbine blade row
design: how much cooling flow the hot section must bleed from the
compressor to hold the blade metal below its allowable temperature.
This leaf implements the standard cooling-effectiveness model in pure
Python, stdlib only. The baseline model is internal convection; an
optional film cooling term adds a fixed effectiveness gain at the
leading edge. It pairs with propulsion/axial-compressor/turbine-stage
for the aerodynamic design of the same blade row and with the
gas-turbine-cycle leaves for the cycle cost of the bleed flow.

## Domain quick reference

- Cooling effectiveness: phi = (T_gas - T_metal_allow) / (T_gas -
  T_coolant). The metal temperature is held a fraction phi of the way
  from the gas temperature down toward the coolant supply temperature.
- Coolant fraction from the energy balance: m_dot_c / m_dot_g =
  phi / (1 - phi) * CP_RATIO. A unit coolant-to-gas specific heat
  ratio (CP_RATIO = 1.0) is the documented simplification for
  conceptual design; the coolant heat capacity rate must offset the
  blade heat load implied by the effectiveness.
- Bleed limit: fractions up to BLEED_LIMIT = 0.20 are practical for a
  blade row; above that the cooling-air penalty on the cycle becomes
  prohibitive and the design must trade metal temperature, gas
  temperature or cooling scheme.
- Film cooling: film at the leading edge lifts the effectiveness by
  FILM_IMPROVEMENT = 0.15 over the internal-convection baseline,
  capped at PHI_CAP = 0.95. The achievable metal temperature is
  T_m = T_gas - phi_eff * (T_gas - T_coolant).
- Margin: margin_k = T_metal_allow - T_m. A positive margin means the
  cooling scheme holds the metal below the allowable temperature.
- Units are SI throughout: K, dimensionless ratios and fractions.

## Workflow

1. Fix the operating point: hot gas total temperature t_gas_k, the
   allowable blade metal temperature t_metal_allow_k and the coolant
   supply temperature t_coolant_k.
2. Compute the required cooling effectiveness with effectiveness;
   the function rejects non-physical inputs with ValueError.
3. Convert the effectiveness into the required coolant-to-gas mass
   flow fraction with coolant_fraction.
4. Check the fraction against the practical bleed limit with
   bleed_verdict; a fraction above 0.20 flags a design that needs
   revisiting.
5. Add the film cooling option: metal_temp_with_film with
   film_cooling=True returns the achievable metal temperature with the
   leading-edge film effectiveness gain.
6. Pull the whole estimate together with analyze, which reports
   effectiveness, coolant_fraction, verdict, metal_temp_k and margin_k
   in one dict.
7. Confirm the deterministic checks with the contract test
   scripts/test_turbine_blade_cooling.py.

## Worked example

Case 1: first blade row, t_gas = 1500 K, allowable metal 1200 K,
coolant 800 K.

- Effectiveness: phi = (1500 - 1200) / (1500 - 800) = 0.4286.
- Coolant fraction: 0.4286 / 0.5714 = 0.75, far above the 0.20 bleed
  limit, verdict "exceeds bleed limit".
- With film: phi_eff = 0.4286 + 0.15 = 0.5786, so
  T_m = 1500 - 0.5786 * 700 = 1095.0 K, margin +105 K. Film cooling
  brings the row inside the allowable metal temperature.

Case 2: high pressure turbine blade with film, t_gas = 1600 K,
allowable 1250 K, coolant 900 K.

- phi = 350 / 700 = 0.5, fraction 1.0, exceeds bleed limit.
- phi_eff = 0.65, T_m = 1600 - 0.65 * 700 = 1145 K, margin +105 K.

Case 3: t_gas = 1600 K, allowable 1350 K, coolant 900 K: phi = 250 /
700 = 0.3571, fraction 0.5556, still exceeds the bleed limit.

Sensitivity: at t_gas = 1500 K and coolant 800 K the required fraction
falls below 0.20 only when the allowable metal temperature exceeds
1383.33 K, about 117 K below the gas temperature.

## Verification

- Confirm effectiveness(1500, 1200, 800) returns 0.4286 and
  coolant_fraction of it returns 0.75.
- Confirm analyze(1500, 1200, 800, film_cooling=True) reports
  metal_temp_k 1095.0 K and margin_k 105.0 K.
- Confirm analyze(1600, 1250, 900, film_cooling=True) reports
  metal_temp_k 1145.0 K.
- Confirm rising allowable metal temperature lowers the required
  fraction monotonically and crosses below 0.20 at 1383.33 K.
- Confirm ValueError rejection: t_gas <= 0, t_gas <= t_coolant,
  t_metal_allow >= t_gas, t_metal_allow <= t_coolant, phi outside
  (0, 1), and negative coolant fractions.
- Run the contract test offline: python3
  scripts/test_turbine_blade_cooling.py (35 tests, deterministic).

## Related leaves

- propulsion/axial-compressor/turbine-stage: the velocity-triangle
  aerodynamic design of the same blade row, the sibling this leaf
  feeds with its allowable metal temperature context.
- propulsion/axial-compressor/multi-stage-compressor: the compression
  system that supplies the cooling bleed flow.
- propulsion/axial-compressor/compressor-map: bleed extraction points
  and their effect on the operating line.
- propulsion/gas-turbine-cycle leaves: the thermodynamic cycle cost of
  the cooling-air bleed.

## Pitfalls

- Accepting a coolant fraction above the bleed limit as a closed
  design: in all three worked-example cases the required fraction (0.75,
  1.0, 0.5556) far exceeds the 0.20 practical bleed limit, and only the
  film-cooling effectiveness gain brings the metal temperature inside —
  the bleed_verdict flags the trade, it does not validate it.
- Neglecting film cooling when the internal-convection fraction is
  prohibitive: adding FILM_IMPROVEMENT = 0.15 at the leading edge lifts
  the effectiveness (0.4286 to 0.5786 in case 1) and turns a 300 K
  over-temperature into a +105 K margin; reporting the baseline-only
  number understates what the row can achieve.
- Setting the allowable metal at or above the gas temperature: the
  effectiveness definition requires t_metal_allow < t_gas and above
  t_coolant; t_metal_allow >= t_gas or t_metal_allow <= t_coolant
  raises ValueError because the metal could not be held.
- Forgetting the film cap: film effectiveness is capped at PHI_CAP =
  0.95, so stacking film on top of an already high effectiveness does
  not keep improving the metal temperature without bound.
- Confusing the margin direction: margin_k = t_metal_allow - T_m is
  positive when the scheme holds the metal below the allowable; a
  negative margin means the metal is too hot, not a safety surplus.
- Reading the coolant fraction without the cycle and model context: the
  0.20 bleed limit exists because the cooling-air penalty becomes
  prohibitive above it (pair with the gas-turbine-cycle leaves), and
  CP_RATIO = 1.0 is a documented conceptual simplification — real
  cooling design needs 3D conjugate heat transfer analysis beyond this
  model.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_turbine_blade_cooling.py

The test covers the three worked-example operating points (effectiveness
within 1e-4, fractions within 1e-3, film metal temperatures within 1.0
K), the bleed-limit verdicts, the film effectiveness cap at 0.95, the
analyze dict outputs and margins, the sensitivity boundary crossing at
1383.33 K with the monotonic trend, and ValueError rejection of every
non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain) and covers engine type certification; the hot-section
  cooling relations above are simplified conceptual-design correlations,
  summary-only per standards-map.yaml. Real cooling design needs 3D
  conjugate heat transfer analysis beyond this model.
- compliance: STANDARDS-REF, gated: false.
