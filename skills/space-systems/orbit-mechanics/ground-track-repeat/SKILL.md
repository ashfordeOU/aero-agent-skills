---
name: ground-track-repeat
description: "Use when you must compute a repeating ground track for a circular Earth orbit: determine the semimajor axis and mean motion from the altitude, evaluate the J2 nodal regression rate, derive the nodal period, count the integer revolutions per sidereal day, and find the repeat cycle in whole days after which the ground track retraces itself. Produces the semimajor axis, mean motion, nodal regression rate, nodal period, revolutions per day, and repeat cycle that gate repeat-ground-track orbit selection for remote sensing and constellation design. Trigger: repeat ground track, ground track repeat, nodal period, revolutions per day, sidereal day, integer revolutions, nodal regression, j2."
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
  tags: [ground-track-repeat, repeat-ground-track, nodal-period, revolutions-per-day, sidereal-day, integer-revolutions, nodal-regression]
  version: 0.1.0
  author: Aero Agent Skills
---

# Repeating Ground Track (space-systems/orbit-mechanics/ground-track-repeat)

Use when the task is repeat ground track orbit design: compute the
nodal period from the mean motion and the J2 nodal regression rate,
count the integer revolutions per sidereal day, and find the repeat
cycle in whole days after which the ground track retraces itself.

## Domain quick reference

- Units: altitude in km in, meters internally, mean motion in rad/s,
  angles in RADIANS out, days as plain integers.
- Constants: Re = 6371000 m, mu = 3.986004418e14 m^3/s^2, J2 =
  1.08262668e-3, sidereal day = 86164.0905 s.
- Semimajor axis: a = Re + altitude_km * 1000 m.
- Mean motion: n = sqrt(mu / a^3) rad/s.
- Nodal regression rate (J2): om_dot = -1.5 * n * J2 * (Re / a)^2 *
  cos(i) rad/s, negative for prograde orbits, positive for
  retrograde inclinations above 90 degrees.
- Nodal period: T_n = 2 pi / (n + om_dot) s, the time between
  successive ascending-node crossings once J2 regression is
  included.
- Revolutions per sidereal day: N = 86164.0905 / T_n. The ground
  track repeats after m whole days when m * N is within tolerance of
  an integer k, giving k revolutions per m days.
- A sun-synchronous orbit at 888.4676 km altitude (i = 97.39 deg)
  has N = 14.000000 revolutions per day: a 1-day repeat track with
  k = 14.
- A sun-synchronous orbit at 562.2007 km has N = 15.000000
  revolutions per day: another 1-day repeat track with k = 15.
- An ISS-like orbit at 400 km, i = 51.6 deg has N = 15.525589: no
  whole-day repeat cycle exists within 60 days.

## Workflow

1. Take the circular orbit altitude in km and the inclination in
   radians.
2. Compute the semimajor axis and mean motion with semimajor_axis
   and mean_motion.
3. Evaluate the nodal regression rate with nodal_regression_rate.
4. Compute the nodal period with nodal_period.
5. Count the revolutions per day with revolutions_per_day.
6. Find the repeat cycle with repeat_cycle_days (m days, k
   revolutions) and pack the full solution with
   ground_track_properties.
7. Gate the orbit selection on the repeat cycle for the remote
   sensing or constellation mission.

## Pitfalls

- Feeding degrees into radian-based functions.
- Using the Keplerian period instead of the nodal period: the J2
  regression shifts the ascending node, so the ground track repeat
  must be counted against the nodal period, not 2 pi / n.
- Declaring a repeat where none exists: the integer-revolution check
  needs a tolerance, and orbits with no integer m * N within the
  search range return no cycle.
- Forgetting the sidereal day (86164.0905 s), not the solar day
  (86400 s), defines the repeat cadence.
- Misreading the regression sign: prograde orbits regress westward
  (negative om_dot), retrograde orbits precess eastward (positive).

## Behavior contract (gate 3)

The semimajor axis, mean motion, nodal regression, nodal period,
revolutions per day, and repeat cycle logic is exercised by the gate
3 contract test: scripts/test_ground_track_repeat.py against
scripts/ground_track_repeat_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_ground_track_repeat.py

## Compliance

- Standards referenced, not reproduced: ECSS series text is
  copyright ESA; the J2 nodal regression and repeat ground track
  condition are common astrodynamics, summary-only per
  standards-map.yaml (ecss is a free ESA download).
- compliance: STANDARDS-REF, gated: false.
