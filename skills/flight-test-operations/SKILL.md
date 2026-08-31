---
name: flight-test-operations
description: "Use when a task concerns flight test operations and envelope expansion: guide the router to the flight-test-operations pack, whose envelope-expansion sub-skill covers corner speed, airspeed classification, and expansion step planning against the load factor envelope, and stall-speed-determination covers reference stall speed from wing loading, weight-corrected stall speed, and stall margin. This pack is the flight test planning and data-reduction layer of the library. Trigger: flight test, envelope expansion, corner speed, load factor, stall speed, airspeed classification, flight test operations, Vs1g."
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
expansion, or stall speed determination.

## Domain

Flight test operations: envelope expansion against the load-factor
envelope and stall speed determination and correction.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| flight-test-operations/envelope/envelope-expansion | Envelope expansion | corner speed, airspeed classes, expansion steps, load factor limits |
| flight-test-operations/performance/stall-speed-determination | Stall speed determination | Vs1g from wing loading, weight-corrected stall speed, stall margin |

## Routing guidance

- Corner speed, maneuver envelope, and expansion step questions route
  to the envelope-expansion sub-skill.
- Stall speed reference and weight-correction questions route to the
  stall-speed-determination sub-skill.
- Airframe performance and certification questions route to their
  domain packs (flight-mechanics, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
