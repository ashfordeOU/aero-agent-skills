---
name: descent-performance
description: "Use when you must compute the descent performance of a fixed-wing aircraft for descent planning: convert the glide slope into the descent gradient, find the rate of descent from the groundspeed and the gradient, estimate the glide range from the aerodynamic efficiency and the height to lose, locate the best glide speed from the wing loading, and plan a step-down descent with the descent distance, the time to descend between flight levels, and the fuel burned in the descent segment. Produces the descent gradient, rate of descent in m/s, glide range in meters, best glide speed, descent time, and descent fuel that gate the descent planning assessment. Trigger: rate of descent, descent gradient, glide range, best glide speed, step-down descent, descent fuel, descent time."
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
  tags: [descent-performance, rate-of-descent, descent-gradient, glide-range, descent-fuel, descent-time, step-down-descent, wing-loading]
  version: 0.1.0
  author: Aero Agent Skills
---

# Descent Performance (flight-mechanics/performance/descent-performance)

Use when the task is descent analysis for planning: descent gradient
and angle, rate of descent, glide range, best glide speed,
step-down descent distance, segment time, and descent fuel for a
fixed-wing aircraft.

## Domain quick reference

- Descent gradient: the vertical path slope tan(gamma),
  dimensionless; percent = gradient * 100. A 3 deg path is a 5.24%
  gradient, about 318 ft per nautical mile (the standard instrument
  glide slope).
- Descent angle: gamma = atan(gradient) in degrees, the inverse of
  the gradient.
- Rate of descent: RoD = groundspeed * gradient in m/s, for a
  constant-gradient path. On shallow paths V * sin(gamma) agrees;
  the gradient form is exact for the path slope.
- Glide range: range = E * height_to_lose in m, the horizontal
  distance covered per unit height lost in a glide, where E = L/D
  (aerodynamic efficiency) in steady gliding flight.
- Best glide speed: v = sqrt(2 W / (rho * S * CL_LDmax)) in m/s,
  the speed at which the glide ratio is maximum, from weight, air
  density, wing area, and the lift coefficient at maximum L/D.
- Top of descent distance: d = height_to_lose / gradient in m, the
  horizontal distance at which a constant-gradient step-down must
  start to reach the target height.
- Descent segment time: t = height_to_lose / RoD in seconds, at a
  constant rate of descent.
- Descent fuel: m_fuel = fuel_flow * t in kg, from the average fuel
  flow (idle or flight-idle thrust) over the segment.
- Units are SI throughout: forces in N (weight W = mass * g0),
  speeds in m/s, angles in degrees, height in m, time in s, fuel in
  kg.
- Descent performance sits in the FAR-25 / CS-25 transport context
  for descent and emergency-descent considerations; the mathematics
  here is standard flight mechanics.

## Workflow

1. Fix the descent strategy: constant-gradient step-down (VNAV
   style) or a glide leg (engine-out case).
2. Convert the path angle to the descent gradient with
   descent_gradient, or a given slope to its angle with
   descent_angle_from_gradient; verify it is positive.
3. Compute the rate of descent with rate_of_descent from the
   groundspeed and the gradient.
4. For a glide leg, estimate the glide range with glide_range and
   the best glide speed with best_glide_speed from weight, density,
   wing area, and CL at max L/D.
5. Plan the step-down: top of descent distance with
   top_of_descent_distance, segment time with descent_time.
6. Compute the descent fuel with descent_fuel from the average fuel
   flow and the segment time.
7. Check the profile against the arrival constraint and the fuel
   reserve before gating.

## Pitfalls

- Mixing mass and weight in best_glide_speed: W is the weight in
  newtons (mass * g0), not mass in kg, or the speed comes out low
  by sqrt(g0).
- Using the air speed instead of the groundspeed for rate of
  descent: the path is flown over the ground, so RoD =
  groundspeed * gradient.
- Feeding the gradient as percent: gradient is dimensionless
  (tan); percent is * 100. Convert before computing RoD or the TOD
  distance.
- Taking the angle for the gradient: descent_gradient takes
  degrees and converts inside; never pre-convert to radians.
- Using the full descent height for one step-down leg: each leg
  loses only its own height step; plan leg by leg.
- A zero gradient means level flight: no descent, no glide range,
  no TOD distance; the functions raise, not divide by zero.
- Dividing instead of multiplying for glide range: range =
  E * height_to_lose, not E / height.

## Behavior contract (gate 3)

The descent gradient, angle, rate of descent, glide range, best
glide speed, TOD distance, segment time, and descent fuel logic is
exercised by the gate 3 contract test:
scripts/test_descent_performance.py against
scripts/descent_performance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_descent_performance.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; descent
  performance from the path slope and glide ratio is common
  flight-mechanics methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
