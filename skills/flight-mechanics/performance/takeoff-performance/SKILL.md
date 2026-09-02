---
name: takeoff-performance
description: "Use when you must compute takeoff performance from the aircraft weight, wing area, and thrust: determine the stall speed from wing loading and density, apply the liftoff speed factor, and estimate the ground roll distance with rolling friction. Produces the stall speed, the lift off speed, and the ground roll distance that gate the takeoff field-length check. Trigger: takeoff, ground roll, lift off speed, stall speed, wing loading."
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
  tags: [takeoff-performance, ground-roll, lift-off-speed, stall-speed, wing-loading, liftoff]
  version: 0.1.0
  author: Aero Agent Skills
---

# Takeoff Performance (flight-mechanics/performance/takeoff-performance)

Use when the task is takeoff performance analysis: stall speed,
lift-off speed, and ground roll distance from weight, wing area,
thrust, and density.

## Domain quick reference

- Stall speed from wing loading: V_s = sqrt(2 * (W/S) / (rho * Cl_max)),
  with wing loading W/S in N/m^2 and air density rho in kg/m^3.
- Stall speed from weight: V_s = sqrt(2 * W / (rho * S * Cl_max)),
  with weight W in N and wing area S in m^2.
- Lift-off speed: V_LOF = 1.2 * V_s (transport convention), speeds in
  m/s.
- Ground roll distance: S_g = 1.44 * W^2 / (g0 * rho * S * Cl_max *
  (T - mu * W)), with thrust T and rolling friction force mu * W in N,
  and g0 = 9.80665 m/s^2.
- Units are SI throughout: forces in N, speeds in m/s, density in
  kg/m^3, wing loading in N/m^2.

## Workflow

1. Collect weight, wing area, thrust, density, and Cl_max.
2. Compute the stall speed with stall_speed or
   stall_speed_from_weight.
3. Apply the liftoff factor with liftoff_speed.
4. Estimate the ground roll with ground_roll_distance.
5. Check thrust against mu * W before reporting a distance.

## Pitfalls

- Using gross weight instead of net thrust minus rolling friction:
  the ground roll needs T - mu * W, not T alone.
- Using a liftoff factor below 1.1: 1.2 is the transport convention;
  values under 1.0 are rejected.
- Mixing kg and N: weight and thrust must be newtons (mass * g0),
  or the distances and speeds come out wrong.

## Behavior contract (gate 3)

The stall speed, liftoff speed, and ground roll logic is exercised by
the gate 3 contract test: scripts/test_takeoff_performance.py against
scripts/takeoff_performance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_takeoff_performance.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; takeoff
  performance is common flight-mechanics methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
