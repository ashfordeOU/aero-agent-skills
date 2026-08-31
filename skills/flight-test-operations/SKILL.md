---
name: flight-test-operations
description: "Use when a task concerns flight test operations, envelope expansion, and performance determination: guide the router to the flight-test-operations pack, whose envelope-expansion sub-skill covers corner speed, airspeed classes, and expansion steps against the load factor envelope, v-speeds covers the certification V-speeds Vref, V2, Vr from the stall speeds and the Vno/Vne guard verdict, stall-speed-determination covers the reference stall speed Vs1g from wing loading with weight correction and stall margin, and accelerate-stop-distance covers the rejected-takeoff accelerate-stop distance from the decision speed V1 with the braking deceleration and the runway fits verdict. This pack is the flight test campaign planning and data-reduction layer of the library. Trigger: flight test, envelope expansion, corner speed, airspeed classes, V-speeds, Vref, V2, Vr, Vno, Vne, stall speed, Vs1g, accelerate stop distance, rejected takeoff, decision speed, V1, runway length."
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
expansion, certification speed determination, or performance
distance checks.

## Domain

Flight test operations: envelope expansion planning, certification
V-speeds, reference stall speed determination, and rejected-takeoff
distance checks.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| flight-test-operations/envelope/envelope-expansion | Envelope expansion | corner speed, airspeed classes, expansion steps, load factor limits |
| flight-test-operations/envelope/v-speeds | V-speeds | Vref, V2, Vr from stall speeds, Vno/Vne guard, certification speeds |
| flight-test-operations/performance/stall-speed-determination | Stall speed determination | Vs1g from wing loading, weight-corrected stall speed, stall margin |
| flight-test-operations/performance/accelerate-stop-distance | Accelerate-stop distance | rejected takeoff, decision speed V1, braking deceleration, runway verdict |

## Routing guidance

- Corner speed, maneuver envelope, and expansion step questions route
  to the envelope-expansion sub-skill.
- Certification speed questions (Vref, V2, Vr, Vno, Vne) route to the
  envelope v-speeds sub-skill.
- Stall speed reference and weight-correction questions route to the
  stall-speed-determination sub-skill.
- Rejected takeoff and accelerate-stop distance questions route to
  the performance accelerate-stop-distance sub-skill.
- Airframe performance and certification questions route to their
  domain packs (flight-mechanics, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
