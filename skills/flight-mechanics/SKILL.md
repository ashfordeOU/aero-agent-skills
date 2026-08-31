---
name: flight-mechanics
description: "Use when a task concerns aircraft flight mechanics and performance: guide the router to the flight-mechanics pack, whose breguet-range sub-skill covers cruise range estimation, takeoff-performance covers ground roll distance, lift-off speed, and stall speed from wing loading, climb-performance covers rate of climb from excess thrust, climb gradient, time to climb, and service ceiling, turn-performance covers turn rate, turn radius, bank angle, load factor, and the sustained turn verdict, and longitudinal-stability covers static longitudinal stability with neutral point and static margin. This pack is the aircraft performance and stability analysis layer of the library. Trigger: flight mechanics, breguet range, cruise range, takeoff performance, ground roll, rate of climb, climb gradient, time to climb, service ceiling, turn rate, turn radius, bank angle, load factor, sustained turn, static margin, neutral point, longitudinal stability."
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
compatibility: "agentskills.io SKILL.md; router/entry point for the flight-mechanics domain pack"
metadata:
  domain: flight-mechanics
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Flight mechanics domain pack (router)

Route here when the task is aircraft performance, range, takeoff,
climb, turn, or static stability.

## Domain

Flight mechanics: cruise performance (Breguet range), takeoff
performance, climb performance, turn performance, and static
longitudinal stability analysis.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| flight-mechanics/performance/breguet-range | Breguet range | cruise range, TSFC, lift-to-drag, fuel fraction, cruise time |
| flight-mechanics/performance/takeoff-performance | Takeoff performance | ground roll distance, lift-off speed, stall speed from wing loading |
| flight-mechanics/performance/climb-performance | Climb performance | rate of climb, excess thrust, climb gradient, time to climb, service ceiling |
| flight-mechanics/performance/turn-performance | Turn performance | turn rate, turn radius, bank angle, load factor, sustained turn |
| flight-mechanics/stability-control/longitudinal-stability | Longitudinal stability | neutral point, static margin, pitch stability coefficient |

## Routing guidance

- Cruise range and fuel-fraction questions route to the
  breguet-range sub-skill; takeoff and ground-roll questions route to
  takeoff-performance.
- Rate of climb, excess thrust, climb gradient, time to climb, and
  service ceiling questions route to the climb-performance sub-skill.
- Turn rate, turn radius, bank angle, and sustained turn questions
  route to the turn-performance sub-skill.
- Neutral point, CG margin, and pitch stability questions route to
  the longitudinal-stability sub-skill.
- Propulsion, structures, and certification questions route to their
  domain packs (propulsion, structures, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
