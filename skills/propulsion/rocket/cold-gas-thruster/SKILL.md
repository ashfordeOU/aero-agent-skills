---
name: cold-gas-thruster
description: "Use when you must size and assess a cold gas thruster for spacecraft reaction control: compute the choked mass flow through the nozzle throat from the plenum pressure and temperature, the thrust from the mass flow and specific impulse, the tank gas mass from the plenum volume and pressure, the isothermal blowdown time constant and pressure history, the operating time to the minimum usable pressure, and the total impulse available over the blowdown. Produces the throat area, mass flow, thrust, tank gas mass, time constant, pressure at a query time, operating time, and total impulse that gate a cold gas RCS sizing. Trigger: cold gas thruster, nitrogen RCS, choked mass flow, plenum blowdown, total impulse, reaction control thruster sizing, isothermal blowdown time constant."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: rocket
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [cold-gas-thruster, nitrogen-rcs, choked-mass-flow, plenum-blowdown, isothermal-blowdown-time-constant, reaction-control-thruster-sizing, total-impulse]
  version: 0.1.0
  author: Aero Agent Skills
---

# Cold Gas Thruster (propulsion/rocket/cold-gas-thruster)

Use when the task is sizing and assessing a cold gas thruster for
spacecraft reaction control: a high pressure inert gas plenum, often
nitrogen, discharges through a choked nozzle throat and produces a
small thrust for attitude control. This leaf implements the standard
cold gas RCS model in pure Python, stdlib only: choked nozzle mass
flow from the plenum pressure and temperature, thrust from the mass
flow and specific impulse, tank gas mass from the ideal gas law,
isothermal blowdown of the plenum, operating time to a minimum usable
pressure, and the total impulse available over the blowdown. It pairs
with propulsion/rocket/rocket-engine-cycle for the feed cycle context
this thruster class replaces on small spacecraft, and with
propulsion/rocket/nozzle-design for the throat and expansion geometry.
The boundary is strict: this leaf is the gas thruster flow and
blowdown model, not a tank structural sizer and not an attitude
control law.

## Domain quick reference

- Choked mass flow: m_dot = P * A* / sqrt(T) * CF_CONST, where
  CF_CONST = sqrt(gamma/R * (2/(gamma+1))^((gamma+1)/(gamma-1))). For
  nitrogen with gamma = 1.4 and R = 296.8 J/(kg K), CF_CONST =
  0.039746. The throat is choked while the plenum pressure ratio stays
  above the critical value, which holds for cold gas blowdown.
- Thrust from mass flow and specific impulse: F = m_dot * Isp * g0
  with g0 = 9.80665 m/s^2. The specific impulse of a cold gas
  thruster is low, typically 40 to 75 s for nitrogen, because the
  stored gas is never heated.
- Tank gas mass: m = P * V / (R * T) from the ideal gas law. A
  25 MPa, 0.03 m3 nitrogen plenum at 293 K holds about 8.62 kg.
- Isothermal blowdown: the tank is thin walled and the discharge is
  slow, so the gas stays near the wall temperature. Mass flow is
  proportional to pressure and the pressure decays exponentially:
  p(t) = p0 * exp(-t / tau) with tau = m_tank / m_dot0. Blowdown from
  25 MPa with a 0.5 mm throat gives tau about 757 s.
- Operating time: t = tau * ln(p0 / p_min) to reach the minimum
  usable pressure p_min at which the thrust stays controllable.
- Total impulse: I = Isp * g0 * (m0 - m_final), the momentum of the
  expelled gas at the fixed specific impulse. Blowing the worked
  plenum down to 2 MPa yields about 5058 Ns.
- Cold gas thrusters suit small spacecraft RCS duty: simple, safe,
  low thrust, modest total impulse; hydrazine and electric options
  carry far more impulse per kilogram when the mission demands it.
- Units are SI throughout: Pa, m3, K, m, kg/s, N, s, Ns.
- ECSS frames the spacecraft propulsion context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Fix the plenum state: pressure P0 in Pa, volume V in m3,
   temperature T in K, throat diameter d in m, specific impulse Isp
   in s and the minimum usable pressure p_min in Pa.
2. Compute the throat area A* = pi * d^2 / 4.
3. Get the initial choked mass flow with choked_mass_flow(P0, T, A*)
   and the thrust with thrust(m_dot, Isp). The mass flow scales
   linearly with plenum pressure.
4. Compute the tank gas mass with tank_gas_mass(P0, V, T) and the
   blowdown time constant with blowdown_time_constant(m, m_dot0).
5. Sample the pressure history with pressure_at_time(P0, t, tau) at
   any requested time, and find the operating time with
   operating_time(P0, p_min, tau).
6. Compute the gas mass left at p_min with tank_gas_mass(p_min, V, T)
   and the total impulse with total_impulse(Isp, m0, m_final).
7. For a one-call sizing, run size_thruster(P0, V, T, d, Isp, p_min,
   t_query) and read all nine outputs from the result dict.
8. Confirm the deterministic checks with the contract test
   scripts/test_cold_gas_thruster.py.

## Worked example

A nitrogen cold gas RCS plenum: P0 = 25 MPa, V = 0.03 m3, T = 293 K,
throat diameter 0.5 mm, Isp = 65 s, p_min = 2 MPa.

- Throat area: A* = pi/4 * (0.5e-3)^2 = 1.9635e-7 m2.
- Initial mass flow: m_dot0 = 25e6 * 1.9635e-7 / sqrt(293) * 0.039746
  = 0.011398 kg/s.
- Thrust: F = 0.011398 * 65 * 9.80665 = 7.265 N.
- Tank gas mass: m0 = 25e6 * 0.03 / (296.8 * 293) = 8.6244 kg.
- Time constant: tau = 8.6244 / 0.011398 = 756.7 s.
- Pressure at 30 s: p = 25e6 * exp(-30 / 756.7) = 24.028 MPa.
- Operating time: t = 756.7 * ln(25 / 2) = 1911.1 s.
- Mass at p_min: m_final = 2e6 * 0.03 / (296.8 * 293) = 0.68995 kg.
- Total impulse: I = 65 * 9.80665 * (8.6244 - 0.68995) = 5057.7 Ns.
- At p_min the flow and thrust scale with pressure: m_dot_min =
  0.000912 kg/s and F_min = 0.581 N, both about 8% of the initial
  values.

## Verification

- Confirm choked_mass_flow(25e6, 293, 1.9635e-7) returns 0.011398
  kg/s and thrust(0.011398, 65) returns 7.265 N.
- Confirm tank_gas_mass(25e6, 0.03, 293) returns 8.6244 kg,
  blowdown_time_constant(8.6244, 0.011398) returns 756.7 s and
  pressure_at_time(25e6, 30, 756.7) returns 24.028 MPa.
- Confirm operating_time(25e6, 2e6, 756.7) returns 1911.1 s and
  total_impulse(65, 8.6244, 0.68995) returns 5057.7 Ns.
- Confirm the mass flow doubles when the plenum pressure doubles, and
  that the pressure decay shape p(tau) = p0 / e holds.
- Confirm every non-positive pressure, temperature, volume, area,
  mass flow, tank mass and isp, every p_min at or above p0, and every
  negative query time raises ValueError.
- Run the contract test offline: python3
  scripts/test_cold_gas_thruster.py (30 tests, deterministic).

## Related leaves

- propulsion/rocket/rocket-engine-cycle: the pressure-fed and pump-fed
  feed cycle context this cold gas thruster class replaces for small
  spacecraft.
- propulsion/rocket/nozzle-design: throat and expansion geometry and
  the exit flow terms for chemical thrusters.
- propulsion/rocket/thrust-vector-control: larger engines steered
  mechanically, the alternative to small RCS thrusters for attitude
  control.
- space-systems/subsystems/propellant-tank-sizing: the plenum tank
  that stores the gas, sized as a pressure vessel.
- propulsion/electric/hall-thruster and the electric pack: the high
  impulse electric alternative for long life station keeping.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_cold_gas_thruster.py

The test covers the worked-example contract (mass flow 0.011398 kg/s,
thrust 7.265 N, tank mass 8.6244 kg, time constant 756.7 s, pressure
24.028 MPa at 30 s, operating time 1911.1 s, total impulse 5057.7 Ns),
the linear scaling of mass flow with pressure, the isothermal
exponential decay shape, the size_thruster chain with all nine output
keys, and ValueError rejection of non-positive pressure, temperature,
volume, throat area, mass flow, tank mass and isp, p_min at or above
p0, and negative query times.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35 is a free ESA
  download (ecss.nl/standards); the cold gas thruster relations above
  are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
