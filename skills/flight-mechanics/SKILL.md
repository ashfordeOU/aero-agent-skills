---
name: flight-mechanics
description: "Use when a task concerns aircraft flight mechanics and performance: guide the router to the flight-mechanics pack, whose breguet-range sub-skill covers cruise range estimation from speed, thrust specific fuel consumption, lift-to-drag ratio, and weights, takeoff-performance covers ground roll distance, lift-off speed, and stall speed from wing loading, and longitudinal-stability covers static longitudinal stability with neutral point, static margin, and the pitch stability coefficient. This pack is the aircraft performance and stability analysis layer of the library. Trigger: flight mechanics, breguet range, cruise range, takeoff performance, ground roll, static margin, neutral point, longitudinal stability."
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
or static stability.

## Domain

Flight mechanics: cruise performance (Breguet range), takeoff
performance, and static longitudinal stability analysis.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| flight-mechanics/performance/breguet-range | Breguet range | cruise range, TSFC, lift-to-drag, fuel fraction, cruise time |
| flight-mechanics/performance/takeoff-performance | Takeoff performance | ground roll distance, lift-off speed, stall speed from wing loading |
| flight-mechanics/stability-control/longitudinal-stability | Longitudinal stability | neutral point, static margin, pitch stability coefficient |

## Routing guidance

- Cruise range and fuel-fraction questions route to the
  breguet-range sub-skill; takeoff and ground-roll questions route to
  takeoff-performance.
- Neutral point, CG margin, and pitch stability questions route to
  the longitudinal-stability sub-skill.
- Propulsion, structures, and certification questions route to their
  domain packs (propulsion, structures, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
