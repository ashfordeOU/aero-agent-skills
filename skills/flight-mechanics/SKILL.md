---
name: flight-mechanics
description: "Use when a task concerns aircraft flight mechanics and performance: guide the router to the flight-mechanics pack, whose breguet-range sub-skill covers cruise range, breguet-endurance covers loiter endurance and holding fuel burn, takeoff-performance covers ground roll and lift-off speed, climb-performance covers rate of climb and service ceiling, turn-performance covers turn rate and load factor, glide-performance covers glide ratio and sink rate, longitudinal-stability covers neutral point and static margin, and lateral-directional-stability covers dihedral effect, directional stability, and Dutch roll. This pack is the aircraft performance and stability analysis layer of the library. Trigger: flight mechanics, breguet range, cruise range, loiter endurance, takeoff performance, ground roll, rate of climb, service ceiling, turn rate, load factor, glide ratio, sink rate, static margin, neutral point, longitudinal stability, lateral directional stability, dihedral, directional stability, Dutch roll."
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

Route here when the task is aircraft performance, range, endurance,
glide, takeoff, climb, turn, or static and lateral-directional
stability.

## Domain

Flight mechanics: cruise performance (Breguet range and endurance),
takeoff performance, climb performance, turn performance, glide
performance, static longitudinal stability, and lateral-directional
stability analysis.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| flight-mechanics/performance/breguet-range | Breguet range | cruise range, TSFC, lift-to-drag, fuel fraction, cruise time |
| flight-mechanics/performance/breguet-endurance | Breguet endurance | loiter endurance, holding time, SFC, fuel burn, final weight |
| flight-mechanics/performance/takeoff-performance | Takeoff performance | ground roll distance, lift-off speed, stall speed from wing loading |
| flight-mechanics/performance/climb-performance | Climb performance | rate of climb, excess thrust, climb gradient, time to climb, service ceiling |
| flight-mechanics/performance/turn-performance | Turn performance | turn rate, turn radius, bank angle, load factor, sustained turn |
| flight-mechanics/performance/glide-performance | Glide performance | glide ratio, descent angle, sink rate, time to descend, unpowered range |
| flight-mechanics/stability-control/longitudinal-stability | Longitudinal stability | neutral point, static margin, pitch stability coefficient |
| flight-mechanics/stability-control/lateral-directional-stability | Lateral-directional stability | dihedral effect, directional stability, vertical tail volume, Dutch roll, roll mode, spiral mode |

## Routing guidance

- Cruise range and fuel-fraction questions route to the
  breguet-range sub-skill; loiter endurance and holding questions
  route to the breguet-endurance sub-skill.
- Takeoff and ground-roll questions route to takeoff-performance.
- Rate of climb, excess thrust, climb gradient, time to climb, and
  service ceiling questions route to the climb-performance sub-skill.
- Turn rate, turn radius, bank angle, and sustained turn questions
  route to the turn-performance sub-skill.
- Glide ratio, descent angle, sink rate, and time-to-descend
  questions route to the glide-performance sub-skill.
- Neutral point, CG margin, and pitch stability questions route to
  the longitudinal-stability sub-skill.
- Dihedral effect, directional stability, Dutch roll, roll mode, and
  spiral mode questions route to the lateral-directional-stability
  sub-skill.
- Propulsion, structures, and certification questions route to their
  domain packs (propulsion, structures, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
