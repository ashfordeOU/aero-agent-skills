---
name: energy-height
description: "Use when you must compute the energy state of an aircraft for performance and maneuverability analysis: derive the specific excess power Ps from thrust, drag, speed, and weight, express the total energy as the energy height combining the geometric altitude with the kinetic height from the airspeed, convert between kinetic and potential energy in climb and cruise trades with the zoom climb gain and the speed bleed for an altitude gain, and recover the speed from a target energy height. Produces the excess power in watts, the specific excess power in m/s, the energy height in meters, the zoom climb gain, and the speed after the energy trade that gate the energy maneuverability assessment. Trigger: energy height, specific excess power, zoom climb, energy maneuverability, kinetic energy."
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
  tags: [energy-height, specific-excess-power, energy-maneuverability, zoom-climb, kinetic-height, excess-power, energy-state]
  version: 0.1.0
  author: AeroSkills
---

# Energy Height and Specific Excess Power (flight-mechanics/performance/energy-height)

Use when the task is the energy state analysis of an aircraft:
specific excess power, energy height, kinetic height, zoom climb,
and the speed-altitude energy trade for performance and
maneuverability assessments.

## Domain quick reference

- Excess power in watts: P_xs = (T - D) * V, with thrust T, drag
  D in newtons (N) and true airspeed V in m/s.
- Specific excess power (the energy rate, in m/s):
  Ps = (T - D) * V / W, with weight W in newtons (N). Ps is the
  rate of change of the energy height and equals the rate of
  climb in steady unaccelerated flight.
- Kinetic height (the speed expressed as an equivalent altitude):
  h_k = V^2 / (2 * g0), with g0 = 9.80665 m/s^2.
- Energy height (total mechanical energy per unit weight):
  h_e = h + V^2 / (2 * g0), with geometric altitude h in meters
  and h_e in meters.
- Zoom climb gain: the extra altitude reachable by converting all
  kinetic energy to potential energy, equal to h_k = V^2 / (2 * g0).
- Speed bleed for an altitude gain (climb-cruise trade):
  V2 = sqrt(V1^2 - 2 * g0 * delta_h), the airspeed left after
  climbing delta_h meters from V1.
- Altitude gain from a speed bleed: delta_h = (V1^2 - V2^2) /
  (2 * g0), the height recovered by slowing from V1 to V2.
- Units are SI throughout: forces in N, speeds in m/s, altitudes
  and heights in m, powers in watts. Energy height analysis sits
  in the FAR-25 / CS-25 transport performance context for climb
  and cruise capability checks.

## Workflow

1. Collect thrust, drag, speed, and weight for the condition.
2. Compute the excess power with excess_power and the specific
   excess power with specific_excess_power.
3. Express the energy state with kinetic_height and energy_height
   from the altitude and the true airspeed.
4. Recover the speed for a target energy height with
   speed_from_energy_height when the reverse question is asked.
5. Trade energy forms with zoom_climb_gain,
   speed_after_climb_bleed, or altitude_from_speed_bleed for the
   climb and cruise exchange.
6. Check that the specific excess power is positive before
   trusting a climb capability verdict.

## Pitfalls

- Using weight in kg instead of newtons: W must be mass * g0, or
  Ps and the energy trade results come out wrong.
- Confusing Ps with excess power: excess power is a rate of energy
  in watts, Ps divides by the weight and is an energy rate in m/s.
- Treating the kinetic height as an airspeed: h_k = V^2 / (2 * g0)
  is a height in meters, not a speed.
- Asking for a speed from an energy height below the geometric
  altitude: the kinetic energy would be negative, so
  speed_from_energy_height raises ValueError.
- Bleeding more speed than the kinetic energy holds: when
  V1^2 - 2 * g0 * delta_h goes negative, the climb is impossible
  and speed_after_climb_bleed raises ValueError.
- Applying the trade formulas to accelerated flight: the energy
  height identity assumes no work beyond the excess power and no
  energy added or removed by the throttle during the exchange.

## Behavior contract (gate 3)

The excess power, specific excess power, energy height, kinetic
height, zoom climb, and speed bleed logic is exercised by the gate
3 contract test: scripts/test_energy_height.py against
scripts/energy_height_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_energy_height.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; energy
  height and specific excess power are common flight-mechanics
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
