---
name: real-cycle-effects
description: "Use when you must compute the real-cycle gas turbine performance with component losses: the compressor exit temperature and the turbine exit temperature from the pressure ratio and the component-efficiency (isentropic-efficiency) of each machine, the real-cycle thermal efficiency of the non-ideal Brayton cycle, the actual-SFC from the efficiency and the fuel lower heating value, and the efficiency penalty from the combustor pressure-loss. Produces the actual station temperatures, the real-cycle efficiency, the actual-SFC, and the pressure-loss penalty in SI units that gate the engine cycle assessment. Trigger: real cycle, component efficiency, isentropic efficiency, pressure loss, combustor loss, actual SFC, off-ideal Brayton."
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
  tags: [real-cycle, component-efficiency, isentropic-efficiency, pressure-loss, combustor-loss, actual-sfc, off-ideal-brayton, component-losses, non-ideal]
  version: 0.1.0
  author: Aero Agent Skills
---

# Real Cycle Effects (propulsion/gas-turbine-cycle/real-cycle-effects)

Use when the task is a non-ideal gas turbine (Brayton) cycle: the
compressor and turbine isentropic efficiencies, the combustor
total-pressure loss, the real thermal efficiency, and the actual
specific fuel consumption. This leaf is the lossy follow-on to the
ideal gas-turbine-cycle leaf: the ideal relations are recovered at
eta_c = eta_t = 1 with no pressure loss.

## Domain quick reference

Units are SI throughout: temperatures in kelvin, pressure ratio
dimensionless, gamma = 1.4 and cp = 1005 J/(kg K) air-standard
values, LHV in J/kg.

- Compressor with isentropic efficiency eta_c:
  T2s = T1 * PR**((gamma-1)/gamma), and the actual exit temperature
  T2 = T1 * (1 + (PR**((gamma-1)/gamma) - 1)/eta_c). Example:
  T1 = 288.15 K, PR = 20, gamma = 1.4, eta_c = 0.85 give T2s about
  678 K and T2 about 747 K. The compressor work per kg is
  w_c = cp * (T2 - T1).
- Turbine with isentropic efficiency eta_t:
  T4s = T3 / PR**((gamma-1)/gamma), and the actual exit temperature
  T4 = T3 - eta_t * (T3 - T4s). Example: T3 = 1500 K, eta_t = 0.88
  give T4s about 637 K and T4 about 741 K. The turbine work per kg
  is w_t = cp * (T3 - T4).
- Real thermal efficiency with the actual temperatures:
  eta_th = (T3 - T4 - T2 + T1)/(T3 - T2) = (w_t - w_c)/q_in; cp
  cancels. The example gives eta_th about 0.40 against the ideal
  cycle value 1 - PR**((1-gamma)/gamma) of about 0.575.
- Specific fuel consumption: SFC = 3600/(eta_th * LHV) with LHV in
  J/kg, the cycle-basis value in kg/(kN*s) at the reference effective
  velocity V_ref = 3.6 m/s (the 3600 factor is the hourly scaling of
  the classic SFC = 3600/(eta * LHV) form). For a real engine scale
  with the effective jet velocity: SFC_T = 1000 * V_eff/(eta_th * LHV)
  in kg/(kN*s) with V_eff in m/s (typical 500 to 700 m/s for a
  turbojet); the example gives SFC about 2.1e-4 kg/(kN*s) on the
  cycle basis and SFC_T about 3.5e-2 kg/(kN*s) at V_eff = 600 m/s.
- Combustor total-pressure loss: PR_eff = PR * (1 - loss_frac) with
  loss_frac the fractional loss (typical 0.02 to 0.06). The
  compressor still sees the full PR; the turbine sees PR_eff, so
  T4s (and T4) rise and the real efficiency falls. Example: a 5%
  loss at PR 20 cuts eta_th from about 0.399 to about 0.388, roughly
  one percentage point; the penalty grows at higher pressure ratio.
- Sensitivity verdicts: d(eta_th)/d(eta_c) > 0 and
  d(eta_th)/d(eta_t) > 0 - improving either component efficiency
  always raises the real cycle efficiency, and the gains flatten as
  the cycle approaches the ideal limit; d(eta_th)/d(loss) < 0 - any
  combustor pressure loss lowers efficiency. At PR 20 the turbine
  efficiency is the stronger lever in the example.

## Workflow

1. Fix the inlet temperature T1, the turbine inlet temperature T3,
   the pressure ratio, gamma, the compressor efficiency eta_c, and
   the turbine efficiency eta_t; add the combustor loss fraction if
   the burner pressure loss matters.
2. Compute the actual compressor exit temperature with
   compressor_exit_temperature(t1, pressure_ratio, gamma, eta_c).
3. Compute the actual turbine exit temperature with
   turbine_exit_temperature(t3, pressure_ratio, gamma, eta_t).
4. Compute the real thermal efficiency with
   real_thermal_efficiency(t1, t2, t3, t4) using the ACTUAL
   temperatures.
5. Compute the actual SFC with sfc_from_efficiency(eta_th, lhv) and,
   when the effective jet velocity is known, the thrust SFC with
   sfc_thrust(eta_th, lhv, v_eff).
6. Apply the combustor loss with pressure_loss_penalty(pr, loss) or
   cycle_efficiency_with_losses(...) and compare against the lossless
   case to size the penalty.
7. Run efficiency_sensitivity() to report which component efficiency
   dominates at the design point.

## Pitfalls

- Passing eta_c or eta_t above 1: non-physical (the exit would be
  colder than isentropic); the module raises ValueError.
- Using the ideal (isentropic) temperatures in the real efficiency:
  T2 and T4 must be the actual lossy station temperatures, and cp
  cancels only when both work terms use the same cp.
- Mixing units: temperatures in kelvin, never Celsius; LHV in J/kg,
  not kJ/kg or MJ/kg, or the SFC shifts by factors of 1000.
- Quoting the efficiency as a percent in the SFC formula: eta_th is
  a fraction (0.4), not 40.
- Forgetting the combustor loss: the turbine sees PR_eff, not the
  full pressure ratio, and the loss compounds at high PR.
- Reading the cycle-basis SFC as a thrust SFC: the 3600/(eta*LHV)
  value carries the reference effective velocity; the thrust value
  needs V_eff, or the answer is off by an order of magnitude.
- Treating the sensitivity verdicts as exact: the derivative signs
  are robust, the magnitudes move with the design point.
- Treating any of this as a certification requirement: FAR-33 sets
  the certification context for aircraft engines; the component
  efficiencies and loss fractions are assessment inputs, and the
  relations above are common cycle assessment practice.

## Behavior contract (gate 3)

The real-cycle relations are exercised by the gate 3 contract test:
scripts/test_real_cycle_effects.py against
scripts/real_cycle_effects.py (stdlib unittest, offline). Run:
python3 scripts/test_real_cycle_effects.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain); the component efficiency and pressure-loss
  relations are common cycle assessment methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
