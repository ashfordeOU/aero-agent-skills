---
name: flight-mechanics
description: "Use when a task concerns aircraft flight mechanics: guide the router to the flight-mechanics pack. breguet-range cruise range, breguet-endurance loiter endurance, specific-range cruise fuel economy, takeoff-performance takeoff distance, climb-performance rate of climb, oei-climb-gradient OEI climb gradient, energy-height specific excess power, descent-performance descent, turn-performance turn rate and load factor, glide-performance glide ratio and sink rate, wind-effects wind triangle and groundspeed, longitudinal-stability neutral point and static margin, lateral-directional-stability dihedral and Dutch roll, dynamic-stability short period and phugoid, trim-analysis stick trim, aileron-reversal control reversal speed. Trigger: flight mechanics, breguet range, loiter endurance, fuel flow, takeoff, rate of climb, OEI, engine out, energy height, specific excess power, descent, turn rate, glide ratio, sink rate, static margin, Dutch roll, phugoid, trim, aileron reversal."
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
glide, takeoff, climb, descent, turn, or static and dynamic stability.

## Domain

Flight mechanics: cruise performance (Breguet range and endurance),
takeoff performance, climb and descent performance, turn performance,
glide performance, static longitudinal stability,
lateral-directional stability, and dynamic stability modes analysis.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| flight-mechanics/performance/breguet-range | Breguet range | cruise range, TSFC, lift-to-drag, fuel fraction, cruise time |
| flight-mechanics/performance/breguet-endurance | Breguet endurance | loiter endurance, holding time, SFC, fuel burn, final weight |
| flight-mechanics/performance/specific-range | Specific air range | specific air range, fuel flow, instantaneous range, fuel burn per sector |
| flight-mechanics/performance/takeoff-performance | Takeoff performance | ground roll distance, lift-off speed, stall speed from wing loading |
| flight-mechanics/performance/landing-performance | Landing performance | landing distance, approach speed, flare, ground roll, stopping distance, reverse thrust, braking coefficient |
| flight-mechanics/performance/climb-performance | Climb performance | rate of climb, excess thrust, climb gradient, time to climb, service ceiling |
| flight-mechanics/performance/descent-performance | Descent performance | descent profiles, glide range, rate of descent, energy management, VNAV step-down planning |
| flight-mechanics/performance/turn-performance | Turn performance | turn rate, turn radius, bank angle, load factor, sustained turn |
| flight-mechanics/performance/glide-performance | Glide performance | glide ratio, descent angle, sink rate, time to descend, unpowered range |
| flight-mechanics/performance/wind-effects | Wind effects | headwind, tailwind, crosswind, wind correction angle, groundspeed, enroute time |
| flight-mechanics/stability-control/longitudinal-stability | Longitudinal stability | neutral point, static margin, pitch stability coefficient |
| flight-mechanics/stability-control/lateral-directional-stability | Lateral-directional stability | dihedral effect, directional stability, vertical tail volume, Dutch roll, roll mode, spiral mode |
| flight-mechanics/stability-control/dynamic-stability | Dynamic stability | short period, phugoid, Dutch roll, spiral, roll subsidence, stability derivatives, damping and frequency |
| flight-mechanics/stability-control/trim-analysis | Trim analysis | stick fixed trim, trim lift coefficient, elevator deflection, trim speed, pitching moment closure |
| flight-mechanics/performance/oei-climb-gradient | OEI climb gradient | OEI thrust, second segment, engine out, approach climb, landing climb gradient |
| flight-mechanics/performance/energy-height | Energy height | specific excess power, energy height, climb/cruise trade, Ps |
| flight-mechanics/stability-control/aileron-reversal | Aileron reversal | control reversal speed, reversal dynamic pressure, torsional stiffness |

## Routing guidance

- Cruise range and fuel-fraction questions route to the
  breguet-range sub-skill; loiter endurance and holding questions
  route to the breguet-endurance sub-skill; specific air range,
  fuel flow, and sector fuel burn questions route to the
  specific-range sub-skill.
- Takeoff and ground-roll questions route to takeoff-performance.
- Landing distance, approach speed, flare, ground roll, and stopping
  distance questions route to the landing-performance sub-skill.
- Rate of climb, excess thrust, climb gradient, time to climb, and
  service ceiling questions route to the climb-performance sub-skill.
- Descent profile, glide-descent range, sink-rate, and energy
  management questions route to the descent-performance sub-skill.
- Turn rate, turn radius, bank angle, and sustained turn questions
  route to the turn-performance sub-skill.
- Glide ratio, descent angle, sink rate, and time-to-descend
  questions route to the glide-performance sub-skill.
- Headwind, crosswind, wind correction angle, groundspeed, and
  enroute time questions route to the wind-effects sub-skill.
- Neutral point, CG margin, and pitch stability questions route to
  the longitudinal-stability sub-skill.
- Dihedral effect, directional stability, Dutch roll, roll mode, and
  spiral mode questions route to the lateral-directional-stability
  sub-skill.
- Short period, phugoid, mode damping, and dynamic stability
  derivative questions route to the dynamic-stability sub-skill.
- Stick fixed trim, elevator deflection, trim speed, and pitching
  moment closure questions route to the trim-analysis sub-skill.
- Propulsion, structures, and certification questions route to their
  domain packs (propulsion, structures, avionics).

- One-engine-inoperative, second segment, approach climb, and landing climb gradient questions route to the oei-climb-gradient sub-skill.
- Energy height and specific excess power questions route to the performance energy-height sub-skill.
- Control reversal speed and reversal dynamic pressure questions route to the stability-control aileron-reversal sub-skill.
## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
