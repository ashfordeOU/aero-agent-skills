---
name: climb-performance
description: "Use when you must compute the climb performance of a fixed-wing aircraft from excess power: derive the rate of climb from thrust, drag, speed, and weight, convert the excess thrust into a climb gradient in percent, estimate the time to climb between two altitudes with the average rate of climb, and locate the service ceiling where the rate of climb decays to 0.5 m/s (100 ft/min). Produces the rate of climb in m/s, the climb gradient, the time to climb, and the service ceiling that gate the climb performance assessment. Trigger: rate of climb, excess thrust, climb gradient, time to climb, service ceiling."
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
  tags: [rate-of-climb, climb-performance, excess-thrust, time-to-climb, service-ceiling, climb-gradient]
  version: 0.1.0
  author: AeroSkills
---

# Climb Performance (flight-mechanics/performance/climb-performance)

Use when the task is climb performance analysis from excess power:
rate of climb, climb gradient, time to climb, and service ceiling
for a fixed-wing aircraft.

## Domain quick reference

- Rate of climb from excess power:
  ROC = (T - D) * V / W, where (T - D) * V is the excess power
  (thrust minus drag times speed) in watts.
- Climb gradient: gamma = (T - D) / W, dimensionless; percent =
  radians * 100.
- Time to climb at the average rate of climb:
  t = delta_h / ((roc_a + roc_b) / 2).
- Service ceiling: the altitude where the rate of climb decays to
  0.5 m/s (100 ft/min); h = (roc_sea_level - 0.5) / lapse_rate,
  assuming a linear ROC lapse with altitude.
- Units are SI throughout: thrust T, drag D, and weight W in
  newtons (N), speed V in m/s, rate of climb in m/s, altitude in
  meters (m), time in seconds (s), gradient in radians (percent is
  dimensionless). A climb exists only when excess thrust T - D is
  positive.
- Climb performance analysis sits in the FAR-25 / CS-25 transport
  performance context for climb and obstacle clearance checks.

## Workflow

1. Collect thrust, drag, speed, and weight.
2. Compute the rate of climb with rate_of_climb; verify the
   excess power is positive before trusting it.
3. Convert the excess thrust to a gradient with climb_gradient.
4. Estimate the time to climb between two altitudes with
   time_to_climb using the rate of climb at each altitude.
5. Locate the service ceiling with service_ceiling from the
   sea-level rate of climb and the ROC lapse rate.
6. Check the climb gradient against the obstacle clearance
   requirement before gating.

## Pitfalls

- Using net thrust instead of excess thrust: the climb is driven
  by T - D, not by T alone; a negative T - D means no climb.
- Mixing weight units: W must be the weight in newtons (mass *
  g0), not mass in kg, or the rate of climb comes out wrong.
- Using a single rate of climb instead of the average: time to
  climb between altitudes needs the mean of roc_a and roc_b.
- Forgetting the 0.5 m/s floor: the service ceiling is where ROC
  decays to 0.5 m/s (100 ft/min), so a sea-level ROC below
  0.5 m/s has no service ceiling in this model.

## Behavior contract (gate 3)

The rate of climb, gradient, time, and ceiling logic is exercised
by the gate 3 contract test: scripts/test_climb_performance.py
against scripts/climb_performance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_climb_performance.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; climb
  performance from excess power is common flight-mechanics
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
