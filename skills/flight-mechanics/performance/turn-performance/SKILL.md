---
name: turn-performance
description: "Use when you must compute sustained turn performance for a fixed-wing aircraft: derive the load factor from the bank angle or the bank angle from the load factor, compute the turn rate and turn radius at a given airspeed, and check whether the available thrust sustains the turn against the increased drag. Produces the load factor, bank angle, turn rate, turn radius, and the sustained verdict that gate the maneuvering performance assessment. Trigger: turn rate, turn radius, bank angle, load factor, sustained turn, level turn, maneuvering performance."
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
  tags: [turn-rate, turn-radius, bank-angle, load-factor, sustained-turn, maneuvering]
  version: 0.1.0
  author: AeroSkills
---

# Turn Performance (flight-mechanics/performance/turn-performance)

Use when the task is sustained turn performance analysis: load
factor from bank angle, turn rate, turn radius, and the sustained
turn verdict against the available thrust for a fixed-wing aircraft.

## Domain quick reference

- Load factor from bank angle: n = 1 / cos(phi), for a level
  coordinated turn, unitless. Bank angle phi is in radians; the load
  factor has no real value at or beyond 90 deg (pi/2 rad).
- Bank angle from load factor: phi = acos(1 / n), in radians, only
  defined for n >= 1.
- Turn rate: omega = g * sqrt(n^2 - 1) / V, in rad/s, with g =
  9.80665 m/s^2 and true airspeed V in m/s.
- Turn radius: R = V^2 / (g * sqrt(n^2 - 1)), in m.
- Sustained turn: the drag in the turn is D_turn = D_level * n
  (level-flight drag scaled by the load factor); the turn is
  sustained when T_available >= D_turn.
- Units are SI throughout: speed V in m/s, radius in m, turn rate in
  rad/s, forces in N, angles in radians, g = 9.80665 m/s^2.
- FAR-25/CS-25 maneuvering requirements frame the load factor
  envelope and the speeds at which turns are flown; the mathematics
  here is standard flight mechanics.

## Workflow

1. Collect the bank angle or the target load factor.
2. Convert with load_factor_from_bank or bank_from_load_factor.
3. Compute the turn rate with turn_rate and the radius with
   turn_radius at the true airspeed.
4. Check the sustained verdict with sustained_check against the
   available thrust and the level-flight drag.
5. Report the load factor, turn rate, radius, and the sustained
   verdict together for the maneuvering assessment.

## Pitfalls

- Mixing radians and degrees: all angles are in radians; feeding 45
  instead of pi/4 corrupts the load factor.
- Using a load factor below 1: level turns need n >= 1; the bank
  angle and turn relations have no real solution below 1 g.
- Forgetting the drag penalty: the drag in the turn is D_level * n,
  not D_level; the sustained verdict needs the increased drag.
- Dividing by V = 0: the turn rate and radius formulas require a
  positive airspeed.
- Treating a not-sustained turn as an error: it is a real verdict to
  report, not an exception.

## Behavior contract (gate 3)

The load factor, bank angle, turn rate, radius, and sustained
verdict logic is exercised by the gate 3 contract test:
scripts/test_turn_performance.py against
scripts/turn_performance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_turn_performance.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; sustained turn
  performance is common flight-mechanics methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
