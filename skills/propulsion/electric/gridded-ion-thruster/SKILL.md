---
name: gridded-ion-thruster
description: "Use when you must size or analyze a gridded ion thruster (Kaufman type) for electrostatic propulsion: ion exhaust velocity and specific impulse from the net beam voltage, Child-Langmuir space-charge limit and perveance margin of the accelerator grid, beam current from extraction area and grid transparency, thrust from beam current and from power with total efficiency, and propellant mass for a delta-v mission. Produces the gridded thruster performance summary with thrust, specific impulse, perveance check, power budget and propellant mass, plus the gridded versus hall comparison at equal power. Trigger: gridded ion thruster, Kaufman thruster, electrostatic propulsion, accelerator grid, perveance, beam extraction, net voltage, ion optics, specific impulse."
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
  tags: [gridded-ion-thruster, kaufman-thruster, electrostatic-propulsion, ion-optics, accelerator-grid, perveance-margin, beam-extraction, net-voltage]
  version: 0.1.0
  author: AeroSkills
---

# Gridded Ion Thruster (propulsion/electric/gridded-ion-thruster)

Use when the task is gridded ion thruster design and performance
analysis for electrostatic propulsion: converting electrical power into
thrust by extracting ions from a discharge plasma and accelerating them
electrostatically through the net voltage between the screen and
accelerator grids of a two-grid (or three-grid) ion optics assembly.
This leaf sizes the thruster from the net beam voltage, the ion optics
geometry and the space-charge perveance limit, and trades the result
against a hall thruster at equal power. It implements the standard
Kaufman thruster performance model in pure Python, stdlib only, with
xenon as the reference propellant. It pairs with
propulsion/electric/hall-thruster, its crossed-field sibling, and with
propulsion/rocket/rocket-sizing for the mission loop.

## Domain quick reference

- Electrostatic acceleration: a singly charged ion extracted from the
  plasma and accelerated through the net beam voltage V_net reaches the
  axial velocity v_i = sqrt(2*e*V_net/m_i), with m_i the ion mass.
  Unlike a hall thruster there is no crossed magnetic field; the ions
  are accelerated by the electric field between the grids only.
- Ion exhaust velocity: v_i = sqrt(2*e*V_net/m_i). For xenon
  (m_i = 2.180e-25 kg, 131.293 u) a 1100 V net voltage gives about
  40209 m/s.
- Specific impulse: I_sp = v_i / g0 with g0 = 9.80665 m/s^2. Gridded
  thrusters run at high net voltage and reach about 3000 to 4500 s at
  1000 to 1500 V, well above hall thrusters.
- Child-Langmuir space-charge limit: the planar current density
  J_CL = (4*eps0/9) * sqrt(2*e/m_i) * V_net^(3/2) / d^2, with eps0 the
  vacuum permittivity and d the effective acceleration gap (screen to
  accelerator grid spacing). The grids cannot extract more than this
  density at a given voltage and gap.
- Beam current with perveance margin: I_b = eta_perv * J_CL * A_extract
  * eta_grid, where eta_perv is the perveance margin (typical 0.4 to
  0.8, the optics run below the space-charge limit) and eta_grid the
  grid transparency (fraction of the extraction plane open to
  beamlets, about 0.6 to 0.7).
- Thrust from the beam current: T = I_b * sqrt(2*m_i*V_net/e) * eta_d,
  valid for singly charged axial ions; eta_d is the divergence
  efficiency, cos of the mean beam half-angle, about 0.98 to 0.995.
- Thrust-to-power: T/P = 2 * eta_T / (g0 * I_sp), the sizing bridge
  between power, efficiency and impulse. Total efficiency eta_T of 0.6
  to 0.7 covers beam, discharge and power processing losses.
- Power chain: beam power P_b = I_b * V_net; total input power
  P_total = P_b / eta_power with eta_power the thruster plus PPU
  efficiency.
- Rocket equation: m_prop = m_dry * (exp(delta_v / (g0 * I_sp)) - 1)
  for a mission with final dry mass m_dry.
- Gridded vs hall at equal power: the gridded thruster gives the higher
  specific impulse (4100 s vs 1600 s typical) and about one fifth of
  the propellant mass flow, but a lower thrust-to-power ratio and a
  lower thrust density, because beam extraction is space-charge limited
  by the Child-Langmuir perveance of the ion optics; the hall thruster
  has no such grid limit in its crossed-field discharge.
- Units are SI throughout: N, m/s, s, W, V, A, m, kg.
- ECSS E-ST-35-03 frames the space propulsion context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: net beam voltage V_net, effective
   screen-to-accelerator gap d, extraction area A_extract, grid
   transparency eta_grid and perveance margin eta_perv, with xenon as
   the default propellant (xenon_ion_mass).
2. Get the ion exhaust velocity with exhaust_velocity and the specific
   impulse with isp_from_net_voltage; confirm I_sp sits in the
   3000 to 4500 s range for a 1000 to 1500 V net voltage.
3. Check the ion optics against the space-charge limit:
   child_langmuir_density gives the maximum extractable current density
   at the gap; beam_current_from_perveance gives the beam current the
   optics deliver at the chosen perveance margin. Verify the margin is
   below one, so the grid design stays under the limit.
4. Compute thrust from the beam current with thrust_from_beam_current,
   applying the divergence efficiency (about 0.985) when the beam
   half-angle is known.
5. Build the power chain: beam_power, then total_power with the
   thruster plus PPU efficiency eta_power; cross-check the sizing with
   thrust_from_power at the total efficiency eta_T.
6. For a mission, size the propellant with
   propellant_mass_for_delta_v and report m_prop and the initial mass.
7. For a technology trade at equal power, run gridded_vs_hall_compare
   and weigh the gridded specific impulse and propellant saving against
   the hall thrust-to-power advantage.
8. Confirm the deterministic checks with the contract test
   scripts/test_gridded_ion_thruster.py.

## Worked example

A gridded ion thruster on xenon: V_net = 1100 V, d = 0.8 mm,
A_extract = 0.028 m^2, eta_grid = 0.68, eta_perv = 0.6, eta_d = 0.985,
eta_T = 0.65.

- Ion mass: m_i = 131.293 * 1.66054e-27 = 2.1802e-25 kg.
- Exhaust velocity: v_i = sqrt(2 * 1.602e-19 * 1100 / 2.1802e-25) =
  40209 m/s.
- Specific impulse: I_sp = 40209 / 9.80665 = 4100 s, inside the
  3000 to 4500 s band for 1100 V net.
- Child-Langmuir limit: J_CL = (4 * 8.854e-12 / 9) * sqrt(2*e/m_i) *
  1100^1.5 / (8e-4)^2 = 272.0 A/m^2.
- Beam current: I_b = 0.6 * 272.0 * 0.028 * 0.68 = 3.107 A, well under
  the 7.62 A the un-margined optics could pass (J_CL * A_extract *
  eta_grid at margin 1).
- Thrust from the beam: T = 3.107 * sqrt(2 * 2.1802e-25 * 1100 / e) *
  0.985 = 0.16744 N.
- Beam power: P_b = 3.107 * 1100 = 3417.5 W. With eta_power = 0.66 for
  the discharge plus PPU chain, P_total = 3417.5 / 0.66 = 5178 W.
- Sizing cross-check: T = 2 * 0.65 * 5178 / (9.80665 * 4100) =
  0.16741 N, within 0.02% of the beam-side thrust, so the 0.65 total
  efficiency and the power chain are consistent.
- Thrust-to-power: T/P_total = 0.16744 / 5178 = 32.3 mN/kW, inside the
  25 to 45 mN/kW gridded band.
- Mission: delta-v 2000 m/s on a 1000 kg dry spacecraft gives
  m_prop = 1000 * (exp(2000 / (9.80665 * 4100)) - 1) = 51.0 kg, initial
  mass 1051.0 kg; the identity (m_dry + m_prop) / m_dry = exp(delta_v /
  (g0 * I_sp)) holds exactly.
- Technology trade at 5000 W against a hall thruster (I_sp 1600 s,
  eta_T 0.5): gridded thrust 0.1617 N against hall 0.3187 N, so the
  hall gives 63.7 mN/kW against 32.3 mN/kW for the gridded, but the
  gridded I_sp is 2.56 times higher and its propellant mass flow about
  0.198 times the hall value.

## Verification

- Confirm exhaust_velocity(1100, m_xe) returns 40208.8 m/s and
  isp_from_net_voltage returns 4100.2 s, within the 3000 to 4500 s
  band at 1100 V.
- Confirm child_langmuir_density(1100, 0.8e-3, m_xe) returns
  271.96 A/m^2 and beam_current_from_perveance(1100, 0.8e-3, 0.028,
  0.68, 0.6, m_xe) returns 3.107 A.
- Confirm thrust_from_beam_current on that beam returns 0.16744 N and
  that the power-bridge value from thrust_from_power(P_total, 0.65,
  4100.2) agrees within 1%.
- Confirm the thrust-to-power ratio on total input power (32.3 mN/kW)
  sits in the 25 to 45 mN/kW gridded band, and that the 167 mN thrust
  at 5.2 kW input matches the 100 to 250 mN band of the 2.3 to 5 kW
  thruster class.
- Confirm propellant_mass_for_delta_v(2000, 1000, 4100.2) returns
  51.0 kg and that (1000 + m_prop) / 1000 equals exp(2000 / (g0 * isp)).
- Confirm gridded_vs_hall_compare(5000, 4100, 1600, 0.65, 0.5) gives a
  hall thrust above the gridded thrust, an I_sp ratio of 2.56 and a
  mass flow ratio of 0.198.
- Confirm every non-positive voltage, gap, area, current, power and
  mass, and every efficiency or perveance margin outside (0, 1] raises
  ValueError.
- Run the contract test offline: python3
  scripts/test_gridded_ion_thruster.py (30 tests, deterministic).

## Related leaves

- propulsion/electric/hall-thruster: the crossed-field sibling; lower
  specific impulse and higher thrust-to-power, for the comparison and
  the technology trade.
- propulsion/rocket/rocket-sizing: the mass and delta-v loop around the
  thruster sizing.
- propulsion/rocket/propellant-selection: propellant families and
  impulse properties for the chemical side of the trade.
- propulsion/rocket/nozzle-design: exit flow and thrust terms for
  chemical thrusters, the alternative to electric propulsion.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gridded_ion_thruster.py

The test covers the 1100 V worked-example contract (exhaust velocity,
specific impulse inside the sanity band, Child-Langmuir density, beam
current from perveance margin and grid transparency, beam-side thrust,
beam and total power, the sizing bridge agreement within 1%, thrust-to-
power in the gridded band, rocket-equation propellant mass), voltage
and gap scaling laws of the space-charge limit, thrust and power chain
scaling, the gridded vs hall comparison at equal power, and ValueError
rejection of non-positive voltage, gap, area, current, power, mass and
out-of-range efficiency or perveance margin.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35-03 is a free ESA
  download (ecss.nl/standards); the gridded ion thruster relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
