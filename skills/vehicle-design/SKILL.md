---
name: vehicle-design
description: "Use when a task concerns aircraft or vehicle conceptual design and sizing: guide the router to the vehicle-design pack: tow-estimation takeoff gross weight, weight-estimation class-I weights, payload-range-diagram payload-range trade, fuselage-sizing cabin layout, tail-sizing tail volume coefficients, landing-gear-sizing strut loads, ws-tw-trade wing loading and thrust-to-weight, fuel-tank-sizing fuel volume and ullage, inertia-estimation moments of inertia, cg-envelope static margin, mass-budget mass rollup and growth allowance, wing-box-sizing spar sizing, fuselage-skin-stringer panel sizing, parametric-cost CERs, operating-cost DOC, life-cycle-cost LCC and learning curves. Trigger: vehicle design, sizing, weight estimation, takeoff gross weight, payload range, fuselage, tail volume, landing gear, strut loads, wing loading, thrust to weight, fuel tank, cg envelope, static margin, mass budget, growth allowance, wing box, spar, skin stringer, parametric cost, direct operating cost, life cycle cost, LCC."
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
| vehicle-design/conceptual/payload-range-diagram | Payload-range diagram | payload vs range trade, max payload, max fuel, design range, ferry range, Breguet range, reserve fuel |
| vehicle-design/sizing/weight-estimation | Weight estimation | class-I weights, weight and balance sheets, component weights |
| vehicle-design/sizing/fuselage-sizing | Fuselage sizing | cabin length and width, fuselage diameter, L/D band, cargo volume check |
| vehicle-design/sizing/tail-sizing | Tail sizing | horizontal and vertical tail volume coefficients, required tail area, tail arm |
| vehicle-design/sizing/control-surface-sizing | Control surface sizing | aileron and elevator and rudder area from control power, roll rate requirement, pitch moment requirement, yaw moment requirement, hinge moment, deflection limits |
| vehicle-design/sizing/landing-gear-sizing | Landing gear sizing | strut load distribution, nose/main gear loads from CG and wheelbase, shock absorber stroke |
| vehicle-design/sizing/ws-tw-trade | W/S and T/W matching | wing loading, thrust-to-weight, matching chart, takeoff/climb/cruise constraints |
| vehicle-design/sizing/wing-planform-sizing | Wing planform sizing | wing area from wing loading and takeoff gross weight, aspect ratio and span, taper ratio and mean aerodynamic chord, sweep angle from cruise Mach |
| vehicle-design/sizing/engine-sizing | Engine sizing | sea-level static thrust, thrust lapse with altitude, takeoff thrust, top-of-climb margin, SFC fuel flow, engine weight |
| vehicle-design/sizing/fuel-tank-sizing | Fuel tank sizing | fuel volume from fuel mass, ullage allowance, required tank volume, wing/fuselage tank capacity fit |
| vehicle-design/mass-properties/inertia-estimation | Inertia estimation | moments of inertia, radius of gyration, parallel axis theorem |
| vehicle-design/mass-properties/cg-envelope | CG envelope | forward and aft limits, static margin from neutral point, envelope polygon, cg excursion with fuel burn |
| vehicle-design/mass-properties/mass-budget | Mass budget | subsystem masses, growth allowance, contingency margin, rollup, MTOW target check |
| vehicle-design/cost-estimation/parametric-cost | Parametric cost | CER, development cost, learning curve, unit cost, program cost |
| vehicle-design/cost-estimation/operating-cost | Operating cost | direct operating cost, block fuel cost, crew cost, maintenance cost, insurance, cost per flight hour |
| vehicle-design/cost-estimation/life-cycle-cost | Life cycle cost | LCC phases, power-law CERs, learning curve Nth unit, present value, inflation, uncertainty |
| vehicle-design/structures-integration/wing-box-sizing | Wing box sizing | root bending moment, spar cap area, shear flow, ultimate load, factor of safety |
| vehicle-design/structures-integration/fuselage-skin-stringer | Fuselage skin-stringer panel | skin thickness, hoop and longitudinal stress, stringer spacing, frame pitch, panel buckling |
| vehicle-design/mdo/multidisciplinary-optimization | Multidisciplinary optimization | MDO, design variables, objective function, constraints, discipline coupling, aero-structural loop, fixed point iteration, design space search |
| vehicle-design/sizing/propeller-sizing | Propeller sizing | propeller diameter, blade count, solidity, activity factor, disk loading, advance ratio, ground clearance |
## Routing guidance

- Takeoff gross weight and fuel-fraction questions route to the
  conceptual tow-estimation sub-skill.
- Payload-range and Breguet-range trade questions route to the
  conceptual payload-range-diagram sub-skill.
- Weight and balance sheet questions route to the weight-estimation
  sub-skill.
- Cabin layout and fuselage diameter questions route to the sizing
  fuselage-sizing sub-skill.
- Empennage sizing questions (tail volume coefficients, required tail
  area) route to the sizing tail-sizing sub-skill.
- Control surface sizing questions (aileron area from the roll rate
  requirement, elevator area from the pitch moment requirement,
  rudder area from the yaw moment requirement, hinge moment,
  deflection limits) route to the sizing control-surface-sizing
  sub-skill.
- Landing gear questions (strut loads, gear loads, shock absorber
  stroke) route to the sizing landing-gear-sizing sub-skill.
- Wing loading and thrust to weight matching questions (the sizing
  matching chart, takeoff distance, climb gradient, and cruise
  constraints) route to the sizing/ws-tw-trade sub-skill.
- Wing planform questions (wing area from wing loading and takeoff
  gross weight, aspect ratio, span, taper ratio, mean aerodynamic
  chord, sweep angle from cruise Mach) route to the sizing
  wing-planform-sizing sub-skill.
- Sea level static thrust, thrust lapse, takeoff thrust, top of climb
  margin, SFC fuel flow, and engine weight questions route to the
  sizing engine-sizing sub-skill.
- Fuel volume, ullage, and tank capacity questions route to the
  sizing fuel-tank-sizing sub-skill.
- Moment of inertia and radius of gyration questions route to the
  mass-properties inertia-estimation sub-skill.
- CG envelope questions (forward/aft limits, static margin, envelope
  polygon, cg excursion) route to the mass-properties cg-envelope
  sub-skill.
- Mass rollup, growth allowance, and contingency margin questions
  route to the mass-properties mass-budget sub-skill.
- Cost estimating relationship and learning curve questions route to
  the cost-estimation parametric-cost sub-skill.
- Direct operating cost, fuel, crew, and maintenance cost questions
  route to the cost-estimation operating-cost sub-skill.
- Life cycle cost, LCC phase, present value, and uncertainty
  questions route to the cost-estimation life-cycle-cost sub-skill.
- Aerodynamic, structural, and certification questions route to their
  domain packs (aerodynamics, structures, avionics).

- Wing box, spar, shear web, and root bending moment sizing questions route to the structures-integration wing-box-sizing sub-skill.
- Fuselage skin thickness, stringer spacing, and frame pitch questions route to the structures-integration fuselage-skin-stringer sub-skill.
- Multidisciplinary optimization, aero-structural coupling loops, fixed-point discipline iteration, and design-space search questions route to the mdo multidisciplinary-optimization sub-skill.
- Propeller diameter, blade count, solidity, activity factor, disk loading, and advance ratio questions route to the sizing propeller-sizing sub-skill.
## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
