---
name: flight-test-operations
description: "Use when a task concerns flight test operations, envelope expansion, performance determination, flutter clearance, and campaign planning: guide the router to the flight-test-operations pack, whose envelope-expansion sub-skill covers corner speed and expansion steps, v-speeds covers Vref, V2, Vr, stall-speed-determination covers Vs1g from wing loading, accelerate-stop-distance covers rejected-takeoff distance from V1, landing-distance-determination covers the FAR 25.125 landing distance with the 1.67 field length factor, flutter-testing covers the 1.2 design dive speed margin and damping trend, and flight-test-planning covers test point build-up and instrumentation. This pack is the flight test campaign planning and data-reduction layer of the library. Trigger: flight test, envelope expansion, corner speed, V-speeds, Vref, V2, Vr, stall speed, Vs1g, accelerate stop distance, rejected takeoff, V1, landing distance, field length, flutter margin, damping trend, frequency separation, test point, instrumentation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; router/entry point for the flight-test-operations domain pack"
metadata:
  domain: flight-test-operations
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Flight test operations domain pack (router)

Route here when the task is flight test planning, envelope
expansion, certification speed determination, performance
distance checks, or flutter clearance.

## Domain

Flight test operations: envelope expansion planning, certification
V-speeds, reference stall speed determination, rejected-takeoff and
landing distance checks, flutter clearance, and campaign planning.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| flight-test-operations/envelope/envelope-expansion | Envelope expansion | corner speed, airspeed classes, expansion steps, load factor limits |
| flight-test-operations/envelope/v-speeds | V-speeds | Vref, V2, Vr from stall speeds, Vno/Vne guard, certification speeds |
| flight-test-operations/performance/stall-speed-determination | Stall speed determination | Vs1g from wing loading, weight-corrected stall speed, stall margin |
| flight-test-operations/performance/accelerate-stop-distance | Accelerate-stop distance | rejected takeoff, decision speed V1, braking deceleration, runway fits |
| flight-test-operations/performance/landing-distance-determination | Landing distance | Vref approach speed, flare segment, braking ground roll, 1.67 field length factor, runway fits |
| flight-test-operations/flutter/flutter-testing | Flutter testing | flutter margin, 1.2 design dive speed, damping trend extrapolation, frequency separation |
| flight-test-operations/planning/flight-test-planning | Flight test planning | test point build-up ordering, instrumentation coverage, campaign plan, prerequisites |

## Routing guidance

- Envelope expansion and corner speed questions route to the
  envelope-expansion sub-skill; certification speed questions route
  to the v-speeds sub-skill.
- Reference stall speed questions route to the
  stall-speed-determination sub-skill.
- Rejected-takeoff distance questions (V1, accelerate-stop) route to
  the accelerate-stop-distance sub-skill.
- Landing distance questions (Vref, flare, ground roll, field length
  factor, runway fits) route to the landing-distance-determination
  sub-skill.
- Flutter clearance questions (flutter margin, damping trend,
  frequency separation, design dive speed) route to the
  flutter-testing sub-skill.
- Test point build-up, instrumentation, and campaign planning
  questions route to the flight-test-planning sub-skill.
- Aircraft performance, structures, and certification questions
  route to their domain packs (flight-mechanics, structures,
  avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
