---
name: low-thrust-spiral
description: "Use when you must size a low-thrust transfer between two circular orbits under continuous thrust with the Edelbaum approximation, for ion propulsion and other electric-propulsion trajectories: compute the circular-orbit velocity at both radii, the total delta-v budget including the inclination change (no-plane-change spiral case as the di = 0 limit), the propellant mass and final mass from the rocket equation at constant thrust and specific impulse, the spiral transfer time, and the impulsive Hohmann delta-v of the same end orbits as comparison. Produces the delta-v budget, propellant mass, final mass, and transfer time that gate low-thrust transfer sizing and trajectory selection. Trigger: low-thrust transfer, Edelbaum, continuous thrust, spiral transfer, inclination change, ion propulsion trajectory, circular orbit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: orbit-mechanics
  tags: [low-thrust-spiral, edelbaum-approximation, continuous-thrust-transfer, spiral-transfer, inclination-change, ion-propulsion-trajectory, circular-orbit-velocity, transfer-time, propellant-mass, electric-propulsion]
  version: 0.1.0
  author: Aero Agent Skills
---

# Low-Thrust Spiral Transfer (space-systems/orbit-mechanics/low-thrust-spiral)

Use when the task is sizing a continuous-thrust orbit transfer: a
low-thrust electric propulsion trajectory that spirals slowly outward
(or inward) between two circular orbits while the thrust also turns
the orbital plane. This leaf implements the Edelbaum approximation,
which closes the delta-v budget, propellant mass, and transfer time
analytically without integrating the spiral. It pairs with the
impulsive-transfer leaves for the low-thrust versus chemical
comparison: hohmann-transfer for the two-impulse coplanar baseline and
lambert-transfer for time-constrained impulsive arcs.

## Domain quick reference

- Circular orbit velocity: v = sqrt(mu / r), with mu the gravitational
  parameter (3.986004418e14 m^3/s^2 for Earth) and r the orbit radius
  in meters. A low earth orbit at 6878 km radius flies at about 7613
  m/s; a geostationary orbit at 42164 km radius flies at about 3075
  m/s.
- Edelbaum delta-v with a total inclination change di in degrees:
  dv = sqrt(v_i^2 + v_f^2 - 2 * v_i * v_f * cos(pi * di_rad / 2)),
  with di_rad = di * pi / 180 and v_i, v_f the circular velocities at
  the inner and outer radii. The approximation assumes the thrust is
  continuously steered so the plane change is spread over the whole
  spiral.
- No-plane-change case: with di = 0 the Edelbaum expression reduces to
  |v_i - v_f|, the pure spiral budget, so the two code paths agree
  exactly. A low-earth to geostationary spiral without a plane change
  costs about 4538 m/s against about 3816 m/s for the impulsive
  Hohmann transfer of the same coplanar radii.
- Exhaust velocity: c = g0 * I_sp with g0 = 9.80665 m/s^2 and I_sp the
  specific impulse in seconds. A 3000 s ion thruster exhausts at about
  29420 m/s.
- Rocket equation: m_final = m0 * exp(-dv / c), propellant mass m_prop
  = m0 - m_final. Continuous thrust buys high specific impulse, so the
  propellant mass is small but the burn is long.
- Transfer time at constant thrust T: t = m_prop * c / T. Thrust is
  low (0.1 to 1 N class), so low-thrust transfers take weeks to
  months, not hours: the worked example below takes about 245 days.
- Hohmann comparison: hohmann_delta_v(r_i, r_f) =
  v_i * (sqrt(2 * r_f / (r_i + r_f)) - 1) +
  v_f * (1 - sqrt(2 * r_i / (r_i + r_f))), the two-impulse budget of
  the same end radii without a plane change, returned as a positive
  magnitude for both transfer directions.
- Units are SI throughout: m, m/s, s, N, kg, and degrees for the
  inclination change.
- ECSS E-ST-10C frames the mission analysis that owns transfer
  sizing; the relations above are standard astrodynamics methodology,
  summary-only.

## Workflow

1. Establish the circular orbit radii r_i and r_f in meters (radius,
   not altitude) and the total inclination change di in degrees; use
   the Earth gravitational parameter unless another central body is
   given.
2. Compute the circular velocities at both radii with
   circular_velocity to know the starting and target speeds.
3. Get the delta-v budget with edelbaum_delta_v(r_i, r_f, di): this is
   the continuous-thrust cost including the plane change. For a
   transfer without an inclination change, read the same answer from
   spiral_no_plane_change_delta_v and confirm the two agree.
4. Size the propulsion with transfer_mass_and_time(dv, m0, thrust,
   isp): propellant mass, final mass, and transfer time for the
   constant-thrust, constant-specific-impulse assumption.
5. Or run low_thrust_transfer_summary(r_i, r_f, di, thrust, isp, m0)
   once for the packed result: v_i, v_f, delta_v, m_prop, mf, and
   t_transfer.
6. Compare against the impulsive baseline with hohmann_delta_v(r_i,
   r_f): the spiral pays roughly 20% more delta-v than the coplanar
   Hohmann transfer for the same radii (about 4538 m/s versus 3816
   m/s for low earth to geostationary), while the Hohmann path needs a
   chemical stage and pays its own plane change.
7. Sanity-check the result: the Edelbaum low-earth to geostationary
   budget with the 28.5 deg inclination change is about 5846 m/s, the
   transfer time for a 0.5 N, 3000 s ion thruster on a 2000 kg bus is
   about 245 days.

## Worked example

Low earth orbit at r_i = 6878 km (500 km altitude, v_i = 7612.68 m/s)
to geostationary orbit at r_f = 42164 km (v_f = 3074.67 m/s), with the
28.5 deg inclination change of the low earth orbit removed during the
spiral. Bus mass m0 = 2000 kg, ion thruster T = 0.5 N at I_sp = 3000 s
(c = 29419.95 m/s).

- Circular velocities: v_i = sqrt(3.986004418e14 / 6878e3) = 7612.68
  m/s, v_f = sqrt(3.986004418e14 / 42164e3) = 3074.67 m/s.
- Edelbaum delta-v: dv = sqrt(7612.68^2 + 3074.67^2 - 2 * 7612.68 *
  3074.67 * cos(pi * 0.4974 / 2)) = 5845.58 m/s, about 5.85 km/s with
  the plane change folded in. With di = 0 the same call returns
  4538.02 m/s, equal to |v_i - v_f|, the pure spiral budget.
- Propellant mass: m_prop = 2000 * (1 - exp(-5845.58 / 29419.95)) =
  360.40 kg, about 18% of the initial mass; mf = 1639.60 kg.
- Transfer time: t = m_prop * c / T = 360.40 * 29419.95 / 0.5 =
  2.1206e7 s, about 245.4 days of continuous thrust.
- Hohmann comparison: the impulsive coplanar budget of the same radii
  is hohmann_delta_v = 3816.09 m/s, so the low-thrust spiral pays
  5845.58 / 3816.09 = 1.53 times the coplanar chemical delta-v, and
  the chemical path would still need its own 28.5 deg plane change.
  The ion option trades that extra delta-v against the much higher
  specific impulse, at the cost of an 8 month transfer.

## Verification

- Confirm edelbaum_delta_v(6878e3, 42164e3, 28.5) returns 5845.58
  m/s (within 1% of the 5840 m/s reference) and that the di = 0 call
  returns 4538.02 m/s, exactly |v_i - v_f|.
- Confirm low_thrust_transfer_summary(6878e3, 42164e3, 28.5, 0.5,
  3000, 2000) returns delta_v 5845.58 m/s, m_prop 360.40 kg, mf
  1639.60 kg, and t_transfer 2.1206e7 s (245.4 days).
- Confirm hohmann_delta_v(6878e3, 42164e3) returns 3816.09 m/s, the
  impulsive comparison, and that the spiral no-plane-change budget
  exceeds it.
- Confirm the rocket equation round trip: mf * exp(dv / c) recovers
  m0, and t_transfer equals m_prop * c / T.
- Confirm every non-positive radius, thrust, initial mass, or specific
  impulse, and every inclination outside [0, 180] degrees raises
  ValueError.
- Run the contract test offline: python3
  scripts/test_low_thrust_spiral.py (35 tests, deterministic).

## Related leaves

- space-systems/orbit-mechanics/hohmann-transfer: the two-impulse
  coplanar transfer that low-thrust spirals compete against.
- space-systems/orbit-mechanics/lambert-transfer: time-constrained
  impulsive transfers for the chemical comparison.
- space-systems/mission-design/mission-delta-v-budget: rolls the
  low-thrust leg into the full mission delta-v and propellant budget.
- space-systems/orbit-mechanics/orbital-perturbations: J2 and drag
  effects that a many-month spiral accumulates.
- space-systems/orbit-mechanics/satellite-coverage: the target orbit
  geometry that motivates the transfer.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_low_thrust_spiral.py

The test covers the low-earth to geostationary sizing contract
(Edelbaum delta-v 5845.58 m/s within 1% of 5840 m/s, the di = 0
identity |v_i - v_f| = 4538.02 m/s, propellant mass 360.40 kg, final
mass 1639.60 kg, transfer time 245.4 days, Hohmann comparison 3816.09
m/s), circular velocity anchors and mu scaling, plane-change-only and
equal-radius boundary cases, inclination range boundaries, the rocket
equation round trip, time-from-propellant consistency, and ValueError
rejection of non-positive radii, thrust, mass, specific impulse, and
out-of-range inclination.

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (systems
  engineering general requirements) frames mission analysis and orbit
  transfer design within the ECSS lifecycle, and the Edelbaum
  approximation and rocket-equation relations above are common
  astrodynamics methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
