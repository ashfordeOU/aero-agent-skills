---
name: hall-thruster
description: "Use when the task is Hall effect thruster (HET) design, sizing, or performance analysis for electric propulsion: thrust from beam current, mass flow and exhaust velocity, specific impulse, thrust-to-power ratio, the total efficiency decomposition (mass, voltage, current and divergence utilization), anode vs total efficiency, discharge power, xenon vs krypton propellant comparison, and propellant mass for a delta-v mission from the rocket equation. Produces the HET performance summary with thrust, mass flow, efficiency terms and a 5 kW class sizing. Trigger: hall thruster, electric propulsion, specific impulse, thrust-to-power, beam current, discharge power, xenon, krypton, propellant mass, delta-v."
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
  tags: [hall-thruster, electric-propulsion, specific-impulse, thrust-to-power, beam-current, xenon, krypton]
  version: 0.1.0
  author: Aero Agent Skills
---

# Hall Effect Thruster (propulsion/electric/hall-thruster)

Use when the task is Hall effect thruster design and performance
analysis for electric propulsion: converting discharge power into
thrust through an axial electric field in a crossed-field discharge,
sizing the thruster from power, efficiency and specific impulse, and
trading xenon against krypton as propellant. This leaf implements the
standard HET performance model (Goebel and Katz style decomposition) in
pure Python, stdlib only. It pairs with propulsion/rocket/rocket-sizing
for the mission loop and propulsion/rocket/propellant-selection for the
propellant families context.

## Domain quick reference

- Thrust law: T = m_dot * v_e, where m_dot is the total propellant mass
  flow and v_e the effective exhaust velocity. The ideal exhaust
  velocity of a singly charged ion accelerated through the beam voltage
  V_b is sqrt(2*e*V_b/m_i); utilization factors multiply it down to the
  effective value.
- Exhaust velocity with utilization: v_e = sqrt(2*e*V_b/m_i) * eta_m *
  eta_d, with eta_m the mass utilization (ion mass flow over total mass
  flow, neutrals do not contribute) and eta_d the divergence efficiency
  cos^2(theta) for a mean beam half-angle theta.
- Thrust from the beam current: T = I_b * sqrt(2*m_i*V_b/e) * eta_d.
  The beam current carries the ion flow directly, so only the
  divergence loss appears.
- Specific impulse: I_sp = v_e / g0, g0 = 9.80665 m/s^2.
- Thrust-to-power: T/P = 2 * eta_T / (g0 * I_sp). This is the sizing
  bridge between power, efficiency and impulse.
- Total efficiency decomposition: eta_T = eta_m * eta_v * eta_c *
  eta_d, where eta_v is the voltage utilization V_b/V_d and eta_c the
  current utilization I_b/I_d (beam current over discharge current).
- Discharge power: P_d = V_d * I_d. The discharge current is the sum of
  the beam current and the electron backflow current, I_d = I_b +
  I_e, so eta_c = I_b/I_d is always below one.
- Anode vs total efficiency: eta_anode = T^2 / (2 * m_dot * P_d) uses
  only discharge power; eta_total = eta_anode * P_d / P_total includes
  magnet, cathode keeper and heater power.
- Propellant comparison: xenon (131.293 u, first ionization 12.13 eV)
  is the reference HET propellant; krypton (83.798 u, 14.00 eV) is
  lighter, so it gives a higher ideal exhaust velocity at the same
  voltage (about 25% higher at 270 V) but costs more ionization energy
  per ion and reaches lower mass utilization in practice.
- Rocket equation: m_prop = m_dry * (exp(delta_v / (g0 * I_sp)) - 1)
  for a mission with final mass m_dry; total initial mass is
  m_dry + m_prop.
- Units are SI throughout: N, kg/s, m/s, s, W, V, A, eV, u.
- ECSS E-ST-35-03 frames the space propulsion context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: discharge power P_d, discharge voltage V_d,
   discharge current I_d (discharge_power), and the propellant.
2. Choose the efficiency decomposition eta_m, eta_v, eta_c, eta_d and
   confirm the implied total efficiency with hall_thruster_efficiency.
3. Get the exhaust velocity: beam voltage V_b = eta_v * V_d, then
   exhaust_velocity with the mass and divergence utilization, or
   isp_from_exhaust_velocity once I_sp is set.
4. Compute thrust from power, total efficiency and specific impulse
   with thrust_from_power, and the mass flow with
   mass_flow_from_thrust.
5. Cross-check the beam side: beam_current from the thrust and beam
   voltage, and beam_current_from_mass_flow from the ionized mass flow;
   the discharge current follows as I_b / eta_c.
6. Compare anode and total efficiency: anode_efficiency on the thrust,
   mass flow and discharge power, then total_efficiency_from_anode with
   the auxiliary power split.
7. For a mission, size the propellant with propellant_mass_for_delta_v
   and report m_prop and the initial mass.
8. For a propellant trade, run xenon_krypton_compare at the beam
   voltage and weigh the exhaust velocity gain of krypton against its
   ionization cost.
9. Confirm the deterministic checks with the contract test
   scripts/test_hall_thruster.py.

## Worked example

A 5 kW class HET on xenon: P_d = 5000 W, eta_T = 0.5, I_sp = 1600 s,
V_d = 300 V.

- Discharge current: I_d = P_d / V_d = 16.67 A (discharge_power
  cross-check: 300 * 16.667 = 5000.01 W).
- Thrust: T = 2 * 0.5 * 5000 / (9.80665 * 1600) = 0.31866 N, within 1%
  of 0.32 N.
- Mass flow: m_dot = T / (g0 * I_sp) = 2.031e-5 kg/s.
- Thrust-to-power: T/P = 6.373e-5 N/W.
- Efficiency decomposition: eta_T = 0.85 * 0.90 * 0.78 * 0.84 = 0.501,
  with eta_m = 0.85, eta_v = 0.90, eta_c = 0.78, eta_d = 0.84. The beam
  voltage is 0.90 * 300 = 270 V and the beam current about
  0.78 * 16.67 = 13.0 A.
- Exhaust velocity check: v_e = g0 * I_sp = 15690.6 m/s; the ideal
  xenon velocity at 270 V is 19921 m/s, so 19921 * 0.85 * 0.84 = 14223
  m/s effective for the beam-only case, with the voltage utilization
  bridging V_b to V_d in the full model.
- Anode vs total: eta_anode = T^2 / (2 * m_dot * P_d) = 0.500. With 300
  W of magnet and cathode power (P_total = 5300 W), eta_total =
  0.500 * 5000 / 5300 = 0.472.
- Mission: delta-v 2000 m/s on a 500 kg dry spacecraft gives
  m_prop = 500 * (exp(2000 / 15690.6) - 1) = 67.97 kg, initial mass
  567.97 kg; the identity (m_dry + m_prop) / m_dry = exp(delta_v / (g0 *
  I_sp)) holds exactly.
- Propellant trade at V_b = 270 V: krypton ideal exhaust velocity
  24935 m/s against xenon 19921 m/s, ratio 1.252, but krypton needs
  14.00 eV per ion against 12.13 eV and its lower mass lowers the mass
  utilization at equal tank pressure, so xenon stays the default for
  high thrust-to-power.

## Verification

- Confirm thrust_from_power(5000, 0.5, 1600) returns 0.31866 N and is
  within 1% of 0.32 N.
- Confirm propellant_mass_for_delta_v(2000, 500, 1600) returns
  67.97 kg and that (500 + m_prop) / 500 equals exp(2000 / (g0 * 1600)).
- Confirm the efficiency product 0.85 * 0.90 * 0.78 * 0.84 equals the
  total efficiency used in the sizing.
- Confirm beam current round-trips: beam_current then
  thrust_from_beam_current recovers the thrust at fixed divergence
  efficiency.
- Confirm every non-positive power, voltage, current, mass, and every
  efficiency outside (0, 1] raises ValueError.
- Run the contract test offline: python3
  scripts/test_hall_thruster.py (30 tests, deterministic).

## Related leaves

- propulsion/rocket/rocket-sizing: the mass and delta-v loop around the
  thruster sizing.
- propulsion/rocket/propellant-selection: propellant families and
  impulse properties for the chemical side of the trade.
- propulsion/rocket/nozzle-design: exit flow and thrust terms for
  chemical thrusters, the alternative to electric propulsion.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hall_thruster.py

The test covers the 5 kW sizing contract (thrust within 1% of 0.32 N,
rocket-equation propellant mass), thrust from power scaling, ideal and
effective exhaust velocity with utilization factors, specific impulse,
thrust-to-power, the efficiency decomposition and its bounds, anode vs
total efficiency with the auxiliary power split, beam current round
trip and beam current from mass flow, discharge power and current, the
xenon vs krypton comparison, and ValueError rejection of non-positive
power, voltage, current, mass and out-of-range efficiency.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35-03 is a free ESA
  download (ecss.nl/standards); the HET performance relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
