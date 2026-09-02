---
name: landing-performance
description: "Use when you must compute the landing performance of the transport airplane: determine the reference approach speed from the stall speed with the 1.3 factor, size the flare radius, flare height, and flare distance from the approach speed and load factor, estimate the air distance over the 50 foot obstacle, and compute the landing ground roll and total stopping distance from the touchdown speed, braking coefficient, lift and drag ratios, and reverse thrust. Produces the approach speed, air distance, ground roll distance, and certified landing field length that gate the FAR 25.125 and CS 25.125 landing distance check. Trigger: landing distance, landing performance, approach speed, flare, ground roll, stopping distance, 50 foot obstacle, reverse thrust, braking coefficient."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [landing-performance, landing-distance, approach-speed, flare-radius, flare-height, flare-distance, ground-roll, stopping-distance, touchdown-speed, braking-coefficient, reverse-thrust, 50-foot-obstacle, air-distance, landing-field-length, certified-landing-distance]
  version: 0.1.0
  author: Aero Agent Skills
---

# Landing Performance (flight-mechanics/performance/landing-performance)

Use when the task is landing performance analysis: reference approach
speed, flare geometry, air distance over the landing obstacle, ground
roll, and stopping distance from the stall speed, weight, braking
coefficient, and reverse thrust.

## Domain quick reference

- Stall speed from wing loading: V_s = sqrt(2 * (W/S) / (rho *
  Cl_max)), with wing loading W/S in N/m^2 and density rho in kg/m^3;
  this is the landing-configuration stall speed the approach speed is
  built on.
- Reference approach speed: V_APP = 1.3 * V_s. FAR 25.125 and CS 25.125
  use 1.3 times the stalling speed in the landing configuration as the
  reference landing speed; 1.23 is the minimum tied to the stall-speed
  definition used in the demonstrated distance.
- Touchdown speed: V_TD = 0.95 * V_APP (transport convention). The
  airplane flares and touches down below the approach speed but still
  well above the stall speed.
- Flare radius: R = V_APP^2 / (g * (n - 1)), with load factor n near 1.2
  in a normal transport landing and g = 9.80665 m/s^2.
- Flare height: h_f = R * (1 - cos(gamma)), the height lost while
  rotating the flight path from the approach angle gamma down to the
  flare (gamma = 3 degrees on a standard glideslope).
- Flare distance: s_f = R * sin(gamma), the horizontal travel during the
  flare arc from flare start to touchdown.
- Air distance over the 50 foot obstacle: s_air = (h_obs - h_f) /
  tan(gamma) + s_f, with h_obs = 15.24 m (50 ft) per FAR 25.125; the
  straight segment at the approach angle down to the flare height plus
  the flare arc.
- Landing ground roll: s_g = V_TD^2 / (2 * a), constant deceleration a
  in m/s^2 from the touchdown speed to a full stop.
- Force balance on the ground roll: a/g = mu * (1 - L/W) + D/W +
  T_rev/W, with mu the braking coefficient, L/W the lift ratio
  (unloaded wheels reduce braking friction), D/W the drag ratio, and
  T_rev/W the reverse thrust ratio. A firm touchdown with weight on the
  wheels gives L/W near zero.
- Certified landing field length: FAR 25.125 requires the landing
  distance measured from 50 feet above the runway to a full stop to be
  multiplied by 1.67 for the published field length (the same 1.67
  factor applies to the dry-runway demonstration; wet-runway and
  contaminated-runway operations apply the operator's additional
  margins).
- Stopping time: t = V_TD / a under constant deceleration.

## Workflow

1. Establish the landing configuration stall speed with stall_speed
   from the wing loading, density, and Cl_max (flaps and gear down).
2. Build the reference approach speed with approach_speed using the 1.3
   factor, then the touchdown speed with touchdown_speed using the 0.95
   factor.
3. Size the flare: flare_radius from the approach speed and load
   factor, then flare_height and flare_distance from the approach
   angle.
4. Estimate the air distance over the 50 foot obstacle with air_distance
   (obstacle height 15.24 m is the FAR 25.125 default).
5. Compute the ground roll: mean deceleration from average_deceleration
   (braking coefficient, lift, drag, and reverse thrust ratios), then
   ground_roll_from_forces, or use ground_roll_distance directly with a
   measured deceleration.
6. Sum the phases with landing_distance and apply the certification
   factor with certified_landing_distance for the published field
   length; check the runway demand with required_braking_coefficient
   when the stop distance is fixed.

## Pitfalls

- Using the approach speed instead of the touchdown speed in the ground
  roll: the ground roll runs from V_TD, not V_APP, and the difference
  is a squared-speed effect on the stopping distance.
- Forgetting the 1.67 certification factor: the demonstrated landing
  distance is not the published field length; FAR 25.125 applies the
  1.67 multiplier.
- Ignoring lift unloading during the roll: with L/W near zero the full
  weight sits on the wheels and mu works at full value; a model that
  carries L/W through the roll weakens the braking friction and
  lengthens the distance.
- Treating the flare as a straight segment: the flare is a circular arc
  at load factor above 1; a straight-line model understates the air
  distance.
- Using an obstacle height at or below the flare height: the obstacle
  must be crossed before the flare arc completes, and air_distance
  rejects that geometry.
- Applying a braking coefficient that cannot be met: required_braking_
  coefficient sizes the friction demand for a target stop distance, and
  a wet or contaminated runway supports far less than the dry 0.4 to
  0.5 range.
- Confusing takeoff ground roll with landing ground roll: takeoff
  accelerates with thrust minus rolling friction; landing decelerates
  with braking friction plus drag plus reverse thrust. The two models
  are not interchangeable.
- Mixing kg and N: weights and thrusts must be in newtons (mass * g0)
  when they enter the force ratios, or the deceleration and distances
  come out wrong.

## Behavior contract (gate 3)

The landing performance math is exercised by the gate 3 contract test:
scripts/test_landing_performance.py against
scripts/landing_performance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_landing_performance.py

## Compliance

- Standards referenced, not reproduced: FAR-25.125 (US government work,
  public domain) and CS-25.125 (free EASA download) frame the landing
  distance certification basis; the approach speed factor, flare
  geometry, and ground roll force balance above are common
  flight-mechanics methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
