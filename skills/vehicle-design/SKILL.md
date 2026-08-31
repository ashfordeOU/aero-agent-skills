---
name: vehicle-design
description: "Use when a task concerns aircraft or vehicle conceptual design and sizing: guide the router to the vehicle-design pack, whose tow-estimation covers takeoff gross weight estimation, weight-estimation covers class-I weights and balance, fuselage-sizing covers cabin layout and diameter, tail-sizing covers tail volume coefficients, landing-gear-sizing covers strut loads and shock absorber stroke, ws-tw-trade covers wing loading and thrust-to-weight matching, inertia-estimation covers moments of inertia, cg-envelope covers forward/aft limits and static margin, parametric-cost covers cost estimating relationships, and life-cycle-cost covers LCC phases, CERs, learning curves, and present value. This pack is the vehicle-level integration layer. Trigger: vehicle design, aircraft design, sizing, weight estimation, weight and balance, center of gravity, takeoff gross weight, fuselage, cabin, tail volume coefficient, landing gear, strut loads, wing loading, thrust to weight, matching chart, moment of inertia, cg envelope, static margin, parametric cost, life cycle cost, LCC, learning curve, present value."
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
gross weight estimation, fuselage and empennage sizing, landing gear
sizing, wing loading and thrust to weight matching, mass properties
(moments of inertia, CG envelope), and cost estimation (parametric
CERs, life cycle cost), tied to the sizing loop that brings
aerodynamic, structural, and performance disciplines together.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| vehicle-design/conceptual/tow-estimation | Takeoff gross weight estimation | fuel-fraction method, empty-weight fraction, sizing iteration |
| vehicle-design/sizing/weight-estimation | Weight estimation | class-I weights, weight and balance sheets, component weights |
| vehicle-design/sizing/fuselage-sizing | Fuselage sizing | cabin length and width, fuselage diameter, L/D band, cargo volume check |
| vehicle-design/sizing/tail-sizing | Tail sizing | horizontal and vertical tail volume coefficients, required tail area, tail arm |
| vehicle-design/sizing/landing-gear-sizing | Landing gear sizing | strut load distribution, nose/main gear loads from CG and wheelbase, shock absorber stroke |
| vehicle-design/sizing/ws-tw-trade | W/S and T/W matching | wing loading, thrust-to-weight, matching chart, takeoff/climb/cruise constraints |
| vehicle-design/mass-properties/inertia-estimation | Inertia estimation | moments of inertia, radius of gyration, parallel axis theorem |
| vehicle-design/mass-properties/cg-envelope | CG envelope | forward and aft limits, static margin from neutral point, envelope polygon, cg excursion with fuel burn |
| vehicle-design/cost-estimation/parametric-cost | Parametric cost | CER, development cost, learning curve, unit cost, program cost |
| vehicle-design/cost-estimation/life-cycle-cost | Life cycle cost | LCC phases, power-law CERs, learning curve Nth unit, present value, inflation, uncertainty |

## Routing guidance

- Takeoff gross weight and fuel-fraction questions route to the
  conceptual tow-estimation sub-skill.
- Weight and balance sheet questions route to the weight-estimation
  sub-skill.
- Cabin layout and fuselage diameter questions route to the sizing
  fuselage-sizing sub-skill.
- Empennage sizing questions (tail volume coefficients, required tail
  area) route to the sizing tail-sizing sub-skill.
- Landing gear questions (strut loads, gear loads, shock absorber
  stroke) route to the sizing landing-gear-sizing sub-skill.
- Wing loading and thrust to weight matching questions (the sizing
  matching chart, takeoff distance, climb gradient, and cruise
  constraints) route to the sizing/ws-tw-trade sub-skill.
- Moment of inertia and radius of gyration questions route to the
  mass-properties inertia-estimation sub-skill.
- CG envelope questions (forward/aft limits, static margin, envelope
  polygon, cg excursion) route to the mass-properties cg-envelope
  sub-skill.
- Cost estimating relationship and learning curve questions route to
  the cost-estimation parametric-cost sub-skill.
- Life cycle cost, LCC phase, present value, and uncertainty
  questions route to the cost-estimation life-cycle-cost sub-skill.
- Aerodynamic, structural, and certification questions route to their
  domain packs (aerodynamics, structures, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
