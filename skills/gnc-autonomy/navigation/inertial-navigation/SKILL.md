---
name: inertial-navigation
description: "Use when you must assess an inertial navigation system (INS): estimate position error growth from accelerometer bias and gyro drift, check the Schuler period and the leveling response, compare strapdown and gimbaled mechanization, and scope alignment and INS/GPS integration. Produces the double-integration position error from an accelerometer bias, the cubic position error from gyro drift, the bounded Schuler steady-state offset, and the Schuler period and frequency. Trigger: inertial navigation, ins, strapdown, gimbaled, gyro drift, accelerometer bias, schuler period, gyrocompass alignment, ins/gps integration, inertial measurement unit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arinc-429
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [inertial-navigation, strapdown, gimbaled, gyro-drift, accelerometer-bias, schuler, gyrocompass, alignment, ins-gps-integration, inertial-measurement-unit]
  version: 0.1.0
  author: AeroSkills
---

# Inertial Navigation (gnc-autonomy/navigation/inertial-navigation)

Use when the task is inertial navigation: mechanization choice,
error growth from sensor imperfections, Schuler tuning, alignment,
and INS/GPS integration.

## Domain quick reference

- An INS measures specific force and rotation rate with
  accelerometers and gyros and integrates them into position,
  velocity, and attitude. It needs no external reference while it
  runs; its errors grow with time.
- Two mechanizations: gimbaled keeps the sensor cluster on a
  stabilized platform driven by torque loops; strapdown mounts the
  cluster rigidly to the vehicle and carries the attitude in
  software (direction cosine matrix or quaternion). Strapdown is the
  standard on modern aircraft; gimbaled survives in some reference
  systems and heritage designs.
- Accelerometer errors: bias, scale factor, misalignment, random
  walk. Bias dominates the position error: double integration of a
  constant bias b gives velocity error b*t and position error
  0.5*b*t^2 (short-time model).
- Gyro errors: bias (drift), scale factor, g-sensitive drift, angle
  random walk. A constant drift eps about a level axis tilts the
  computed vertical and couples gravity; the position error grows as
  (1/6)*g*eps*t^3, the cubic term that limits an unaided INS.
- Schuler tuning: the level loop is tuned as a pendulum of length
  equal to the Earth radius, so the natural period is
  T = 2*pi*sqrt(R/g) = 84.4 min. A Schuler-tuned INS does not
  diverge from leveling errors; they oscillate at the Schuler
  frequency, and a constant accelerometer bias settles to the
  bounded offset b*R/g (about 650 m per mg).
- Alignment: leveling with accelerometers (gravity defines the
  vertical) and gyrocompassing with the Earth-rate vector
  (7.2921159e-5 rad/s; the north component omega_e*cos(lat) defines
  north). Azimuth alignment takes minutes and is set by gyro noise.
- INS/GPS integration: the GPS solution bounds the unbounded INS
  errors, and the INS bridges GPS outages and smooths the output.
  Loosely coupled (position and velocity updates into the navigation
  filter), tightly coupled (raw pseudorange and carrier phase), or
  deeply coupled (aiding inside the receiver). GPS errors are
  bounded; INS errors are bounded only by aiding.
- Key numbers: g0 = 9.80665 m/s^2; mean Earth radius 6371 km;
  Schuler period 84.4 min; Earth rate 7.2921159e-5 rad/s;
  1 deg/h = 4.848e-6 rad/s.
- ARINC 429 (reference-only) is the civil data bus over which
  inertial reference systems broadcast attitude, heading, position,
  and velocity; the standard is cited, never copied.

## Workflow

1. Choose the mechanization: strapdown (software attitude) unless
   the design is a gimbaled reference system.
2. Convert the gyro drift with deg_per_hour_to_rad_s(deg_per_hour)
   before it enters any growth model.
3. Estimate the short-time bias error with
   accel_bias_position_error(bias, t) and the velocity error with
   accel_bias_velocity_error(bias, t).
4. Estimate the cubic gyro error with
   gyro_drift_position_error(deg_per_hour, t); this term usually
   sets the unaided error budget.
5. Check the loop tuning with schuler_period() and
   schuler_frequency(); confirm 84.4 min.
6. Bound the long-time bias error with
   schuler_steady_state_error(bias).
7. Resolve the Earth rate for gyrocompassing with
   earth_rate_component(lat_rad).
8. Accumulate gyro noise with
   angle_random_walk_sigma(arw_deg_per_sqrt_h, t_hours).
9. Scope the integration: loosely coupled when the receiver
   delivers a position and velocity solution; tighter coupling when
   raw measurements and a shared filter are available.

## Pitfalls

- Double counting the bias error: 0.5*b*t^2 is the short-time free
  response; over tens of minutes the Schuler loop bends it into the
  bounded b*R/g offset. Quote both, and say which applies.
- Forgetting the cubic gyro term: at 0.001 deg/h it is about 370 m
  after one hour, at 0.01 deg/h about 3.7 km. Gyro drift, not
  accelerometer bias, usually sets the unaided budget.
- Mixing units: deg/h must convert to rad/s (1 deg/h = 4.848e-6
  rad/s) before the growth formulas.
- Treating the Schuler period as a damping time: it is an
  oscillation period, not a settling time; errors oscillate at
  84.4 min rather than decay.
- Confusing specific force with acceleration: accelerometers measure
  specific force, so gravity must be modeled and removed in the
  integration.
- Forgetting that azimuth alignment needs Earth-rate sensing: the
  north component shrinks as cos(lat), so gyrocompassing degrades at
  high latitude.

## Behavior contract (gate 3)

The Schuler quantities, bias and drift error growth, steady-state
offset, Earth-rate components, and random-walk accumulation are
exercised by the gate 3 contract test:
scripts/test_inertial_navigation.py against
scripts/inertial_navigation_logic.py (stdlib unittest, offline).
Run:
python3 skills/gnc-autonomy/navigation/inertial-navigation/scripts/test_inertial_navigation.py

## Compliance

- ARINC 429 is proprietary (ARINC/SAE ITC); inertial reference
  systems on civil aircraft broadcast over it. Name and paraphrase
  only per standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
