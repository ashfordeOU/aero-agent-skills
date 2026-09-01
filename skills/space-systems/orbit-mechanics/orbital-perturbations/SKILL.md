---
name: orbital-perturbations
description: "Use when you must quantify the J2 secular perturbations of a circular Earth orbit: compute the RAAN drift rate and the argument-of-perigee drift from the mean motion, semimajor axis, and inclination, derive the nodal period change against the Keplerian period, and scale the perturbation magnitude with altitude from LEO to GEO. Produces drift rates in radians per second and degrees per day, the critical inclination, and the oblateness acceleration ratio. Trigger: orbital-perturbations, j2-nodal-regression, raan-drift, argument-of-perigee-drift, secular-drift, nodal-precession, nodal period change, perigee drift."
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
  tags: [orbital-perturbations, j2-nodal-regression, raan-drift, argument-of-perigee-drift, secular-drift, nodal-precession]
  version: 0.1.0
  author: AeroSkills
---

# Orbital Perturbations (space-systems/orbit-mechanics/orbital-perturbations)

Use when the task is secular J2 perturbation analysis of an Earth
orbit: the RAAN drift rate, the argument-of-perigee drift, the nodal
period change, and how the perturbation magnitude falls with
altitude. All numbers below were verified by running
scripts/orbital_perturbations_logic.py and by a J2 numerical
propagation of the circular orbit.

## Domain quick reference

Constants: Re = 6371000 m, mu = 3.986004418e14 m^3/s^2,
J2 = 1.08262668e-3. Semimajor axis a = Re + altitude_km * 1000 (m),
mean motion n = sqrt(mu / a^3), Keplerian period T_K = 2 pi / n.

- RAAN drift rate: om_dot = -1.5 * n * J2 * (Re / a)^2 * cos(i)
  rad/s. At 500 km, i = 30 deg: -1.3403e-6 rad/s, which is
  -6.6352 deg/day. Zero at i = 90 deg, positive for retrograde
  orbits. At GEO (35786 km, i = 30 deg): -0.0116 deg/day, about
  572x smaller because the rate scales as a^-3.5.
- Argument-of-perigee drift: w_dot = 0.75 * n * J2 * (Re / a)^2 *
  (5 cos^2(i) - 1) rad/s. At 500 km, i = 30 deg: +2.1281e-6 rad/s,
  which is +10.5347 deg/day. The drift is zero at the critical
  inclination 63.435 deg, positive below it, negative between
  63.435 deg and 116.565 deg.
- Nodal period: T_n = 2 pi / (n + om_dot) s (the ground-track
  convention, consistent with the ground-track-repeat leaf). At
  500 km, i = 30 deg: T_K = 5668.14 s, T_n = 5675.01 s, so the
  nodal period change dT = T_n - T_K = +6.86 s (prograde orbits
  lengthen). At i = 90 deg, dT = 0; at i = 97.4 deg (sun-
  synchronous retrograde), dT = -1.02 s (shortens).
- Draconitic period (exact ascending-node crossing interval):
  T_d = 2 pi / (M_dot + w_dot), with M_dot = n + 0.75 * n * J2 *
  (Re / a)^2 * (3 cos^2(i) - 1). At 500 km, i = 30 deg: 5652.36 s
  (about 16 s shorter than T_K); at i = 90 deg: 5676.07 s (longer).
- Perturbation magnitude versus altitude: the J2 acceleration ratio
  to two-body is (3/2) * J2 * (Re / a)^2. At 500 km: 1.3962e-3; at
  GEO: 3.7077e-5, about 38x smaller. Drift rates fall even faster,
  as a^-3.5, so LEO-sized drift does not exist at GEO.

## Workflow

1. Take the altitude in km and the inclination in radians; compute
   a, n, and T_K with semimajor_axis, mean_motion, keplerian_period.
2. Compute the RAAN drift with raan_drift_rate and convert to
   degrees per day with rad_per_s_to_deg_per_day.
3. Compute the argument-of-perigee drift with arg_perigee_drift_rate
   and check the sign against the critical inclination
   (critical_inclination_rad).
4. Derive the nodal period and its change with nodal_period and
   nodal_period_change; use the draconitic period
   (draconitic_period) for the true node-crossing cadence.
5. Scale the perturbation with altitude using
   perturbation_magnitude_ratio; compare LEO and GEO magnitudes.
6. Pack the full solution with secular_drift_properties and report
   rates in degrees per day for mission planning.

## Pitfalls

- Confusing this leaf with sun-synchronous-inclination: that leaf
  solves for the inclination that makes the RAAN drift match the
  sun; this leaf takes the inclination as given and quantifies the
  drifts, periods, and magnitudes. Do not call the sun-synchronous
  solver when the task is drift rates for an arbitrary given orbit.
- Confusing this leaf with hohmann-transfer: a Hohmann transfer
  changes the orbit radius with two impulsive burns; perturbations
  drift the elements continuously with no propulsion. A perigee
  drift is not a perigee-raising burn.
- Forgetting the RAAN drift sign: negative for prograde (i < 90
  deg), zero at i = 90 deg, positive for retrograde; cos(i) flips
  the sign.
- Assuming the perigee always advances: w_dot is positive only
  below the critical inclination 63.435 deg, negative between
  63.435 deg and 116.565 deg, and positive again above.
- Using the Keplerian period for node-based cadence: the nodal
  period 2 pi / (n + om_dot) differs from T_K by about 7 s per
  orbit at 500 km, i = 30 deg, and the difference accumulates over
  a mission.
- Mixing the two period conventions: the nodal period 2 pi / (n +
  om_dot) (ground-track convention) is not the draconitic period
  2 pi / (M_dot + w_dot); they differ by about 23 s at 500 km,
  i = 30 deg.
- Expecting LEO-sized drift at high altitude: the magnitude ratio
  falls as (Re / a)^2 and the drift rates as a^-3.5; at GEO the
  RAAN drift is about 572x smaller than at 500 km.
- Feeding degrees into radian-based functions, or quoting rad/s
  rates as deg/day without conversion.

## Behavior contract (gate 3)

The RAAN drift, argument-of-perigee drift, nodal period change,
draconitic period, and magnitude logic is exercised by the gate 3
contract test: scripts/test_orbital_perturbations.py against
scripts/orbital_perturbations_logic.py (stdlib unittest, offline,
27 test methods). Run:
python3 scripts/test_orbital_perturbations.py

## Compliance

- Standards referenced, not reproduced: the ECSS series text is
  copyright ESA; the J2 secular rates and the draconitic period are
  common astrodynamics, summary-only per standards-map.yaml (ecss
  is a free ESA download).
- compliance: STANDARDS-REF, gated: false.
