---
name: electrothermal-thruster
description: "Use when you must compute the electrothermal thruster operating point for electric propulsion: useful heating power from input power and heating efficiency, propellant mass flow from chamber temperature rise, ideal vacuum exhaust velocity, thrust, specific impulse, thrust efficiency and thrust-to-power ratio for a resistojet or arcjet family point. Produces a single-point performance summary with the power budget decomposition and a typical-band verdict. Trigger: electrothermal thruster, resistojet, arcjet, heated propellant, power to thrust, ammonia, nitrogen, hydrogen, helium propellant, specific impulse."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: electric
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: electric
  tags: [electrothermal-thruster, electric-propulsion, resistojet, arcjet, heated-propellant, power-to-thrust, specific-impulse]
  version: 0.1.0
  author: Aero Agent Skills
---

# Electrothermal Thruster (propulsion/electric/electrothermal-thruster)

Use when the task is resistojet or arcjet performance analysis for
electric propulsion: heating a working gas (NH3, N2, H2 or He) with
electrical power, expanding the heated propellant through a vacuum
nozzle, and reporting the single operating point. This leaf converts
input electrical power into useful heating power, sizes the mass flow
from the chamber temperature rise, and computes exhaust velocity,
thrust, specific impulse, thrust efficiency and thrust-to-power in
pure Python, stdlib only. It covers one operating point of a resistojet
or arcjet, not a mission loop. It pairs with propulsion/rocket/
rocket-sizing for the delta-v loop and with its electrostatic siblings
in the same pack, which own accelerated-beam claims; this leaf only
heats propellant, so it neither accelerates charged beams nor uses
extraction electrode assemblies.

## Domain quick reference

- Useful heating power: P_heat = eta_heat * P_elec, with eta_heat the
  heating efficiency (default 0.85 resistojet family, 0.7 arcjet
  family). eta_heat folds in heat lost to the structure and radiation.
- Mass flow: m_dot = P_heat / (cp * (T_0 - T_in)), sized so the useful
  heating power raises propellant enthalpy from the plenum temperature
  T_in to the chamber temperature T_0.
- Ideal exhaust velocity (vacuum form): v_e = sqrt(2 * cp * eta_nozzle
  * T_0). With p_e = 0 the pressure-ratio term
  (1 - (p_e/p_0)^((gamma-1)/gamma)) collapses to one and gamma drops
  out; eta_nozzle (default 0.9) folds in frozen-flow and
  finite-area-ratio losses of a real resistojet nozzle.
- Thrust: F = m_dot * v_e, the pressure term (p_e - p_a) * A_e
  vanishing for a fully expanded vacuum nozzle with p_e = 0.
- Specific impulse: I_sp = v_e / g0, g0 = 9.80665 m/s^2.
- Thrust efficiency: eta_t = F^2 / (2 * m_dot * P_elec), jet power over
  input power. Exact model identity: eta_t = eta_heat * eta_nozzle *
  T_0 / (T_0 - T_in), because v_e credits the full chamber enthalpy
  cp * T_0 including the inlet enthalpy the propellant carries in from
  the plenum at T_in; the product eta_heat * eta_nozzle is recovered
  only in the limit T_in -> 0 (see Verification).
- Thrust-to-power: F / P_elec in N/W; report mN/kW by scaling by 1e6.
- Propellant table (300 K values, reference-only): NH3 cp 2090 J/(kg K)
  gamma 1.31; N2 cp 1040, gamma 1.40; H2 cp 14300, gamma 1.41; He cp
  5190, gamma 1.67.
- Typical operating bands (published ranges, reported not enforced):
  resistojet I_sp 200-350 s, arcjet I_sp 400-700 s.
- Units are SI throughout: W, K, kg/s, m/s, N, s.
- ECSS E-ST-35-03 frames the space propulsion context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: input power P_elec (W), chamber
   temperature T_0 (K), plenum temperature T_in (K) and the propellant
   (one of NH3, N2, H2, He). Confirm the family: resistojet or arcjet.
2. Look up propellant properties with propellant_properties; cp and
   gamma are 300 K reference values used for the heating and the
   sanity checks.
3. Convert power to heat: useful_heating_power(eta_heat, p_elec) gives
   P_heat. The default eta_heat is 0.85 for resistojets and 0.7 for
   arcjets when run through electrothermal_performance.
4. Size the flow: mass_flow_from_heating(p_heat, cp, t0, t_in) gives
   the mass flow that the useful heating power can raise from T_in to
   T_0.
5. Get the exhaust velocity: exhaust_velocity_ideal(cp, eta_nozzle,
   t0) is the vacuum form, then specific_impulse(v_e) and
   thrust_from_mass_flow(mdot, v_e) give I_sp and thrust.
6. Close the power budget: thrust_efficiency(f, mdot, p_elec) and
   thrust_to_power(f, p_elec) report eta_t and the thrust-to-power
   ratio; scale the latter by 1e6 for mN/kW.
7. Check the family band: operating_band_verdict(isp, family) reports
   whether the point lies in the typical resistojet (200-350 s) or
   arcjet (400-700 s) range. The bands are reported, never enforced.
8. Run the whole point through electrothermal_performance(p_elec, t0,
   t_in, propellant, eta_heat=..., eta_nozzle=..., family=...) to get
   the full summary dict in one call, including the decomposition of
   heating loss and nozzle loss.
9. Confirm the deterministic checks with the contract test
   scripts/test_electrothermal_thruster.py.

## Worked example

Resistojet on ammonia: P_elec = 1000 W, T_0 = 1200 K, T_in = 300 K,
eta_heat = 0.85, eta_nozzle = 0.9, family resistojet.

- Useful heating power: P_heat = 0.85 * 1000 = 850 W.
- Mass flow: m_dot = 850 / (2090 * (1200 - 300)) = 4.5189e-4 kg/s,
  close to 4.52e-4 kg/s.
- Exhaust velocity: v_e = sqrt(2 * 2090 * 0.9 * 1200) = 2124.7 m/s,
  close to 2125 m/s. Ideal vacuum expansion of the full chamber
  enthalpy, frozen-flow and area-ratio losses folded into eta_nozzle.
- Thrust: F = 4.5189e-4 * 2124.7 = 0.9601 N, about 960 mN.
- Specific impulse: I_sp = 2124.7 / 9.80665 = 216.7 s, inside the
  typical resistojet band of 200-350 s.
- Thrust efficiency: eta_t = F^2 / (2 * m_dot * P_elec) = 1.020. The
  exact model identity eta_t = eta_heat * eta_nozzle * T_0 /
  (T_0 - T_in) = 0.85 * 0.9 * 1200 / 900 = 1.02 holds because the
  vacuum exhaust velocity credits the full chamber enthalpy cp * T_0,
  which includes the enthalpy the propellant already carries at the
  300 K plenum. In this ideal accounting the jet power is charged
  against electrical input only, so eta_t can exceed the simple
  eta_heat * eta_nozzle product whenever T_in > 0 (see Verification).
- Thrust-to-power: F / P_elec = 9.60e-4 N/W = 960 mN/kW.
- Nozzle check: the nozzle-converted useful heating is eta_nozzle *
  P_heat = 765 W of the 850 W heating power; the remaining jet power
  traces to the inlet enthalpy carried into the chamber.

## Verification

- Confirm propellant_properties("NH3") returns (2090.0, 1.31) and the
  other table entries match the reference values.
- Confirm useful_heating_power(0.85, 1000) is 850 W, and
  mass_flow_from_heating(850, 2090, 1200, 300) is 4.5189e-4 kg/s.
- Confirm exhaust_velocity_ideal(2090, 0.9, 1200) is 2124.7 m/s, so
  I_sp is 216.7 s and thrust is 0.9601 N.
- Confirm the ideal-model identity: thrust_efficiency on the point
  equals eta_heat * eta_nozzle * T0 / (T0 - T_in) within 1e-6. The
  spec's simplified identity eta_t = eta_heat * eta_nozzle is the
  T_in -> 0 limit of the exact relation; with a 300 K plenum the
  carried-in enthalpy raises the ratio above the simple product. This
  is a recorded assumption of the ideal model, not a violation of
  energy conservation across the full power budget.
- Confirm I_sp scales with sqrt(T_0) at fixed cp: doubling T_0 from
  1200 K to 4800 K doubles v_e.
- Confirm thrust scales linearly with mass flow at fixed v_e.
- Confirm eta bounds: eta_heat and eta_nozzle outside (0, 1], power
  at or below zero, T_0 <= T_in, T_in <= 0, cp <= 0, non-finite
  inputs and unknown propellants or families all raise ValueError.
- Run the contract test offline: python3
  scripts/test_electrothermal_thruster.py (26 tests, deterministic).

## Related leaves

- propulsion/electric/hall-thruster and
  propulsion/electric/gridded-ion-thruster: electrostatic siblings in
  the same electric pack; they accelerate beams, this leaf heats
  propellant. Same power train, different acceleration mechanism.
- propulsion/rocket/rocket-sizing: the delta-v and propellant mass
  loop around a single thruster operating point.
- propulsion/rocket/propellant-selection: propellant families and
  impulse properties for the broader trade.

## Pitfalls

- Reading the > 1 thrust efficiency as free energy: eta_t = 1.020 in
  the worked example is the ideal-model identity
  eta_heat * eta_nozzle * T_0 / (T_0 - T_in), which exceeds the simple
  product whenever the plenum temperature T_in > 0 because the vacuum
  exhaust velocity credits the full chamber enthalpy including the
  carried-in inlet enthalpy — a recorded assumption of the ideal
  model, not a conservation violation.
- Using the simplified efficiency as the exact relation: eta_t =
  eta_heat * eta_nozzle is only the T_in -> 0 limit; with a 300 K
  plenum the exact identity must be used, and the two disagree by the
  T_0 / (T_0 - T_in) factor.
- Feeding a chamber temperature at or below the plenum: the mass flow
  is sized on the rise (T_0 - T_in), so T_0 <= T_in raises ValueError —
  the thruster must heat the propellant above its inlet state.
- Reporting the operating band as a pass or fail: the 200-350 s
  resistojet and 400-700 s arcjet bands are published ranges that
  operating_band_verdict reports but never enforces; a point outside
  the band is not an error.
- Confusing the electrostatic siblings with this leaf: hall and gridded
  thrusters accelerate charged beams through crossed fields or grids,
  while this leaf only heats propellant and uses no extraction
  electrodes — do not apply the perveance or beam-current machinery
  here.
- Forgetting the vacuum-nozzle assumption: v_e uses the vacuum form
  where the pressure-ratio term collapses and gamma drops out, and the
  thrust has no (p_e - p_a) * A_e term — the model is not a
  finite-back-pressure nozzle analysis.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_electrothermal_thruster.py

The test covers the resistojet worked-example contract (P_heat 850 W,
mass flow 4.52e-4 kg/s, exhaust velocity 2125 m/s, thrust 0.96 N,
I_sp 217 s in the resistojet band), the ideal-model thrust-efficiency
identity, sqrt(T_0) scaling of exhaust velocity, linear scaling of
thrust with mass flow, higher T_0 giving higher I_sp, arcjet defaults
and band verdicts, the propellant table, efficiency bounds, and
ValueError rejection of non-physical power, temperature ordering,
propellant and family names, efficiency values and non-finite inputs.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35-03 is a free ESA
  download (ecss.nl/standards); the electrothermal performance
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
