---
name: sun-synchronous-inclination
description: "Use when you must compute the sun-synchronous orbital inclination from altitude for a circular Earth orbit: determine the orbital mean motion from the semimajor axis, evaluate the J2 nodal regression rate, solve the sun-synchronous condition cos(i) = -omega_dot_desired / (1.5 n J2 (Re/a)^2), and produce the inclination in radians and degrees. Produces the altitude, semimajor axis, mean motion, and inclination that gate dawn-dusk and local-time-of-ascending-node orbit selection. Trigger: sun-synchronous orbit, inclination, nodal regression, ascending node, local solar time, dawn-dusk, j2."
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
  tags: [sun-synchronous, inclination, nodal-regression, ascending-node, local-solar-time, dawn-dusk, retrograde]
  version: 0.1.0
  author: AeroSkills
---

# Sun-Synchronous Inclination (space-systems/orbit-mechanics/sun-synchronous-inclination)

Use when the task is sun-synchronous orbit design: compute the
mean motion, the J2 nodal regression rate, and the inclination that
makes the ascending node precess with the sun, keeping the local
solar time fixed.

## Domain quick reference

- Units: altitude in km in, meters internally, mean motion in
  rad/s, inclination in RADIANS out, degrees for display.
- Semimajor axis: a = Re + altitude_km * 1000 m (altitude in km
  converted to m), with Re = 6371000 m and mu = 3.986004418e14 m^3/s^2.
- Mean motion: n = sqrt(mu / a^3) rad/s.
- Nodal regression: om_dot = -1.5 * n * J2 * (Re / a)^2 * cos(i)
  rad/s, with J2 = 1.08262668e-3.
- Sun-synchronous condition: cos(i) = -omega_dot_desired /
  (1.5 * n * J2 * (Re / a)^2), omega_dot_desired = 2 pi / 365.2421897
  / 86400 rad/s, one revolution per tropical year.
- At 500 km altitude the solution is 97.39 deg: sun-synchronous
  orbits are always retrograde.
- Above roughly 6000 km no sun-synchronous inclination exists: the
  required cos(i) leaves [-1, 1] and the solver raises ValueError.

## Workflow

1. Take the circular orbit altitude in km.
2. Compute the semimajor axis and mean motion with
   orbital_mean_motion.
3. Solve the inclination with sun_synchronous_inclination (radians).
4. Check the regression rate with nodal_regression_rate.
5. Pack the full solution with sun_synchronous_properties.
6. Gate the orbit selection on the 97-99 deg retrograde band for LEO.

## Pitfalls

- Feeding degrees into radian-based functions.
- Negative altitude or an inclination outside [0, pi] raising
  ValueError.
- Forgetting that high altitudes have no solution: the solver
  raises instead of returning a nonsense angle.
- Misreading the sign: the regression rate is negative for prograde
  orbits, and the sun-synchronous inclination is always above 90
  degrees.

## Behavior contract (gate 3)

The mean motion, nodal regression, and inclination logic is
exercised by the gate 3 contract test:
scripts/test_sun_synchronous.py against
scripts/sun_synchronous_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_sun_synchronous.py

## Compliance

- Standards referenced, not reproduced: ECSS series text is
  copyright ESA; the J2 nodal regression and sun-synchronous
  condition are common astrodynamics, summary-only per
  standards-map.yaml (ecss is a free ESA download).
- compliance: STANDARDS-REF, gated: false.
