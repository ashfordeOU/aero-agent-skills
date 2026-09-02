---
name: combustor-design
description: "Compute the gas turbine combustor design point: the stoichiometric fuel-air-ratio from the fuel carbon and hydrogen mass fractions, the operating fuel-air-ratio from the fuel and air flows, the equivalence ratio, the combustion efficiency, the heat release from the fuel flow and lower heating value, and the temperature rise across the combustor with the adiabatic flame temperature estimate from a constant-specific-heat energy balance. Produces the fuel flow, heat release, combustor exit temperature, and flame temperature that gate the combustor design assessment. Use when the task is combustor sizing, burner fuel-air ratio, flame temperature, or heat release for a gas turbine engine. Trigger: combustor design, fuel air ratio, adiabatic flame temperature, combustion efficiency, heat release."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: gas-turbine-cycle
  tags: [combustor-design, fuel-air-ratio, stoichiometric-fuel-air-ratio, adiabatic-flame-temperature, combustion-efficiency, heat-release]
  version: 0.1.0
  author: Aero Agent Skills
---

# Combustor Design (propulsion/gas-turbine-cycle/combustor-design)

Use when the task is the gas turbine combustor design point: the
stoichiometric and operating fuel-air ratio from fuel properties and
burner flows, the equivalence ratio, the combustion efficiency, the
heat release and temperature rise across the combustor, and the
adiabatic flame temperature estimate from a simple constant-specific-
heat energy balance.

## Domain quick reference

All values below are computed by scripts/combustor_design_logic.py
(stdlib only, deterministic) and verified by running it.

Kerosene-class fuel: carbon mass fraction c = 0.86, hydrogen mass
fraction h = 0.14, lower heating value LHV = 43.2 MJ/kg. Air is
23.2% oxygen by mass.

- Oxygen demand per kg of fuel: m_O2 = (32/12) * c + 8 * h.
  For kerosene: 2.6667 * 0.86 + 8.0 * 0.14 = 3.4133 kg O2 per kg fuel.
- Stoichiometric fuel-air ratio: far_st = 0.232 / m_O2 = 0.0680.
  (Methane, c = 0.75, h = 0.25, gives far_st = 0.0580; a carbon-rich
  fuel has a higher far_st because carbon needs less oxygen per kg.)
- Operating fuel-air ratio: far_op = m_fuel / m_air. At m_fuel =
  2.0 kg/s and m_air = 100 kg/s: far_op = 0.0200.
- Equivalence ratio: phi = far_op / far_st = 0.0200 / 0.0680 = 0.2943
  (fuel-lean, phi < 1).
- Combustion efficiency: eta_b = actual rise / ideal rise. With
  actual = 706.563 K and ideal = 713.7 K: eta_b = 0.9900.
- Heat release: Q = eta_b * m_fuel * LHV = 0.99 * 2.0 * 43.2e6 =
  85.54e6 W, about 85.5 MW.
- Temperature rise across the combustor: delta_T = Q / (m_air * cp)
  = 85.54e6 / (100.0 * 1150.0) = 743.8 K. At compressor exit
  T2 = 700 K the combustor exit is T3 = 1443.8 K, near 1444 K.
- Adiabatic flame temperature estimate (constant specific heat):
  T_ad = T_in + eta_b * LHV * far / (cp_products * (1 + far)).
  Lean point (far = 0.0200, cp = 1300 J/(kg K)): T_ad = 1345.1 K.
  Stoichiometric point (far = 0.0680): T_ad = 2793.8 K, which
  overestimates the real flame temperature (roughly 2300 to 2400 K
  for kerosene in air) because dissociation is not modeled.

Units: flows in kg/s, LHV in J/kg, cp in J/(kg K), temperatures in
kelvin, heat release in watts.

## Workflow

1. Fix the fuel composition (c, h mass fractions) and the lower
   heating value; compute far_st with stoichiometric_far.
2. Fix the burner fuel and air flows; compute far_op with
   operating_far and the equivalence ratio with equivalence_ratio.
3. Determine the combustion efficiency from the measured and ideal
   temperature rise with combustion_efficiency.
4. Compute the heat release with heat_release and the temperature
   rise with temperature_rise; add the rise to the compressor exit
   temperature for the combustor exit temperature.
5. Estimate the adiabatic flame temperature with
   adiabatic_flame_temperature at the operating and stoichiometric
   fuel-air ratios.
6. Report fuel flow, heat release, combustor exit temperature, and
   flame temperature estimate.

## Pitfalls

- Confusing this leaf with gas-turbine-cycle: that leaf computes the
  ideal Brayton cycle efficiency and station temperatures from the
  pressure ratio; the combustor block (fuel-air ratio, heat release,
  temperature rise, flame temperature) belongs here.
- Confusing this leaf with turbofan-cycle: bypass ratio, propulsive
  efficiency, and specific thrust are turbofan-cycle; the combustor
  design point of the core sits in combustor-design even for a
  turbofan engine.
- Using the higher heating value instead of the lower heating value:
  LHV must be used because water leaves the combustor as vapor.
- Treating the constant-cp flame temperature as exact: dissociation
  lowers the real stoichiometric flame temperature to about 2300 to
  2400 K for kerosene in air; report the simple value as an estimate.
- Calling the operating fuel-air ratio stoichiometric: far_st for
  kerosene is near 0.068; far_op is typically 0.015 to 0.03, and
  phi = far_op / far_st is the lean/rich measure.
- Using the primary-zone air flow instead of the total combustor air
  flow: the mean exit temperature rise uses the full air flow
  including dilution air.
- Unit slips: LHV in J/kg with flows in kg/s gives watts; cp in
  J/(kg K); temperatures in kelvin, never Celsius.
- Fuel composition checks: c + h must sum to about 1 (trace elements
  are not supported); the functions raise ValueError on non-physical
  inputs instead of returning nonsense.

## Behavior contract (gate 3)

The combustor relations above are exercised by the gate 3 contract
test: scripts/test_combustor_design.py against
scripts/combustor_design_logic.py (stdlib unittest, offline,
26 test methods). Run:

python3 skills/propulsion/gas-turbine-cycle/combustor-design/scripts/test_combustor_design.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain) and covers engine type certification, not combustor
  analysis methods; the fuel-air ratio, heat release, and flame
  temperature relations are common-knowledge combustion
  thermodynamics, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
