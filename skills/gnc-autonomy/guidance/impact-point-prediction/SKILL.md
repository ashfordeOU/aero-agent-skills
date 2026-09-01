---
name: impact-point-prediction
description: "Compute the ballistic impact point prediction for a projectile from launch position, launch speed, and flight path angle: determine the flat earth vacuum range with the range equation, the time of flight, the impact coordinates from the launch point and heading, and the sensitivity of the landing point to initial condition errors. Use when a task asks where a round will land, how long the ballistic flight lasts, or how launch speed and flight path angle errors displace the impact point. Trigger: impact point prediction, ballistic trajectory, range equation, time of flight, flight path angle, launch speed, impact coordinates, flat earth."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: guidance
  tags: [impact-point-prediction, ballistic-trajectory, range-equation, time-of-flight, flight-path-angle, launch-speed, projectile-landing, flat-earth-vacuum]
  version: 0.1.0
  author: AeroSkills
---

# Impact Point Prediction (gnc-autonomy/guidance/impact-point-prediction)

Use when the task is predicting where an unguided ballistic projectile
lands from its launch state: range, time of flight, impact
coordinates, and how sensitive the landing point is to launch speed
and flight path angle errors.

## Domain quick reference

Flat earth, vacuum ballistic model, point mass launched from (x0, y0)
with speed v0 and flight path angle theta0 above the horizontal, in a
constant gravity field g. Angles are radians throughout; units are m,
s, m/s, m/s^2.

- Range: R = v0^2 * sin(2 * theta0) / g. Worked anchor: v0 = 100 m/s,
  theta0 = 45 deg, g = 9.81 m/s^2 gives R = 10000 / 9.81 =
  1019.37 m.
- Time of flight: T = 2 * v0 * sin(theta0) / g. Same anchor gives
  T = 14.42 s.
- Peak height: hp = (v0 * sin(theta0))^2 / (2 * g). Same anchor gives
  hp = 254.84 m.
- Impact coordinates: xf = x0 + R * cos(heading),
  yf = y0 + R * sin(heading), heading the azimuth from the +x axis.
  Anchor: heading = 30 deg gives (882.80, 509.68) m from the origin.
- Range sensitivity: dR/dv0 = 2 * v0 * sin(2 * theta0) / g and
  dR/dtheta0 = 2 * v0^2 * cos(2 * theta0) / g. At the anchor,
  dR/dv0 = 20.39 m per (m/s) and dR/dtheta0 = 0: the range is
  first-order flat in angle at the 45 deg maximum.
- Error propagation: delta_R = dR/dv0 * dv0 + dR/dtheta0 * dtheta,
  and delta_T = dT/dv0 * dv0 + dT/dtheta0 * dtheta with
  dT/dv0 = 2 * sin(theta0) / g, dT/dtheta0 = 2 * v0 * cos(theta0) / g.
  Anchor: dv0 = 1 m/s moves the impact point 20.39 m and shifts the
  time of flight 0.144 s.
- FAR-25 and CS-25 (reference-only) frame airworthiness certification
  for transport airplanes; the flat earth range equation itself is
  common ballistic knowledge.

## Workflow

1. Confirm the model applies: an unguided projectile in a flat earth
   vacuum field, no drag, no curvature. For long ranges or high
   speeds, treat the result as a first estimate only.
2. Convert theta0 and the heading to radians if given in degrees.
3. Compute range_flat_earth(v0, theta0, g) and
   time_of_flight(v0, theta0, g); both validate v0 > 0, theta0 in
   (0, pi/2), and g > 0.
4. Compute impact_point(x0, y0, v0, theta0, heading, g) for the
   absolute landing coordinates, remembering the launch position
   offset.
5. Compute range_sensitivity(v0, theta0, g), then
   impact_error(v0, theta0, dv0, dtheta, g) with the launch condition
   uncertainties to size the landing point dispersion.
6. Bundle the full prediction with
   impact_point_prediction(x0, y0, v0, theta0, heading, g), which
   returns range, time of flight, peak height, and impact coordinates
   in one dict.
7. State the model limitations with the numbers: drag, curvature, and
   wind are outside this model and dominate at long range.

## Pitfalls

- Confusing impact point prediction with proportional-navigation: PN
  computes a commanded acceleration from closing velocity and line of
  sight rate inside an intercept guidance loop; impact point
  prediction is open-loop ballistic geometry with no guidance law.
- Confusing with pursuit-guidance: pursuit steers the interceptor
  velocity at the target using an aim heading and capture condition;
  the ballistic round here is unguided and never steers.
- Confusing with command-to-line-of-sight: CLOS keeps a missile on the
  tracker to target line with a steering command; impact point
  prediction has no tracker line and no steering.
- Confusing with rendezvous-phasing: phasing sizes orbital catch-up
  maneuvers with delta-v around a circular orbit; impact point
  prediction is a flat earth ground impact problem with no orbit.
- Mixing degrees and radians: theta0 and heading must be radians, or
  every range and coordinate is wrong by a large factor.
- Treating the vacuum range as the true range: drag shortens the
  range, and Earth curvature lengthens it at long ranges; the model is
  a first estimate, not a fire control solution.
- Assuming one error source dominates: at 45 deg the angle sensitivity
  is exactly zero, so speed errors dominate there, while away from
  45 deg angle errors dominate; always check both partial
  derivatives.
- Forgetting the launch position offset: impact_point returns absolute
  coordinates from (x0, y0); dropping the offset shifts the whole
  prediction.

## Behavior contract (gate 3)

The range equation, time of flight, peak height, impact coordinates,
range sensitivity, first-order error propagation, and the bundled
prediction dict are exercised by the gate 3 contract test:
scripts/test_impact_point_prediction.py against
scripts/impact_point_prediction_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_impact_point_prediction.py

## Compliance

- FAR-25 (US government work, public domain) and CS-25 (EASA,
  free-download) are referenced by id only per standards-map.yaml,
  reference-only: true; no text is copied.
- compliance: STANDARDS-REF, gated: false.
