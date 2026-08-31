---
name: vehicle-design
description: "Use when a task concerns aircraft or vehicle conceptual design and sizing: guide the router to the vehicle-design pack, whose tow-estimation sub-skill covers takeoff gross weight estimation with fuel-fraction and empty-weight fractions, weight-estimation covers class-I weight estimation, center of gravity, and CG envelope checks, ws-tw-trade covers wing loading and thrust to weight matching with takeoff, climb, and cruise constraints for the sizing matching chart, inertia-estimation covers moments of inertia and the parallel axis theorem, and parametric-cost covers cost estimating relationships, learning curves, and unit and program cost. This pack is the vehicle-level integration and sizing layer of the library. Trigger: vehicle design, aircraft design, sizing, weight estimation, weight and balance, center of gravity, takeoff gross weight, wing loading, thrust to weight, matching chart, moment of inertia, radius of gyration, parametric cost, learning curve, cost estimating relationship."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; router/entry point for the vehicle-design domain pack"
metadata:
  domain: vehicle-design
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Vehicle design domain pack (router)

Route here when the task is aircraft or vehicle conceptual design,
sizing, mass properties, or cost estimation.

## Domain

Vehicle design and integration: class-I weight estimation, takeoff
gross weight estimation, wing loading and thrust to weight matching,
mass properties (moments of inertia), and parametric cost
estimation, tied to the sizing loop that brings aerodynamic,
structural, and performance disciplines together.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| vehicle-design/conceptual/tow-estimation | Takeoff gross weight estimation | fuel-fraction method, empty-weight fraction, sizing iteration |
| vehicle-design/sizing/weight-estimation | Weight estimation | class-I weights, CG, envelope, weight and balance sheets |
| vehicle-design/sizing/ws-tw-trade | W/S and T/W matching | wing loading, thrust-to-weight, matching chart, takeoff/climb/cruise constraints |
| vehicle-design/mass-properties/inertia-estimation | Inertia estimation | moments of inertia, radius of gyration, parallel axis theorem |
| vehicle-design/cost-estimation/parametric-cost | Parametric cost | CER, development cost, learning curve, unit cost, program cost |

## Routing guidance

- Takeoff gross weight and fuel-fraction questions route to the
  conceptual tow-estimation sub-skill.
- Weight and CG questions route to the weight-estimation sub-skill.
- Wing loading and thrust to weight matching questions (the sizing
  matching chart, takeoff distance, climb gradient, and cruise
  constraints) route to the sizing/ws-tw-trade sub-skill.
- Moment of inertia and radius of gyration questions route to the
  mass-properties inertia-estimation sub-skill.
- Cost estimating relationship and learning curve questions route to
  the cost-estimation parametric-cost sub-skill.
- Airfoil and polar questions route to the aerodynamics pack.
- Structure and materials questions route to the structures pack.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
