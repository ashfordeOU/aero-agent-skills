---
name: propulsion
description: "Use when a task concerns aircraft or rocket propulsion: guide the router to the propulsion pack, whose gas-turbine-cycle and regenerative-cycle sub-skills cover Brayton cycle and regenerator efficiency, turbofan-cycle and bypass-ratio-trade cover turbofan parameters and bypass design, rocket-sizing, nozzle-design, and propellant-selection cover rocket sizing, nozzles, and propellant trade, and axial-compressor-stage and compressor-map cover stage velocity triangles and compressor operating maps. This pack is the propulsion performance and sizing layer of the library. Trigger: propulsion, gas turbine, Brayton cycle, regenerator, turbofan, bypass ratio, rocket equation, delta-v, rocket nozzle, area ratio, exit Mach, propellant, density impulse, axial compressor, compressor map, surge margin, corrected flow, multi-stage compressor, off-design turbofan, real cycle, component efficiency."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; router/entry point for the propulsion domain pack"
metadata:
  domain: propulsion
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Propulsion domain pack (router)

Route here when the task is engine cycle analysis, turbofan
performance parameters, rocket sizing, rocket nozzles, rocket
propellant selection, or axial compressor maps and stages.

## Domain

Propulsion: gas turbine and turbofan thermodynamic cycle analysis
(simple and regenerative Brayton), turbofan bypass design trades,
launch-vehicle rocket sizing with the rocket equation and staging,
rocket nozzle design, rocket propellant selection, and axial
compressor stage and operating-map analysis.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| propulsion/gas-turbine-cycle/gas-turbine-cycle | Gas turbine cycle | Brayton thermal efficiency, compressor/turbine exit temperatures, pressure ratio |
| propulsion/gas-turbine-cycle/regenerative-cycle | Regenerative cycle | regenerator effectiveness, regenerative cycle efficiency, optimum pressure ratio, efficiency gain |
| propulsion/gas-turbine-cycle/real-cycle-effects | Real cycle effects | component efficiency, isentropic efficiency, pressure loss, actual exit temperatures, real SFC |
| propulsion/turbofan/turbofan-cycle | Turbofan cycle | bypass ratio, propulsive efficiency, specific thrust, fan/core mass flow |
| propulsion/turbofan/bypass-ratio-trade | Bypass ratio trade | BPR vs TSFC, thrust split, specific thrust, fan pressure ratio |
| propulsion/turbofan/turbofan-off-design | Turbofan off-design | corrected mass flow, corrected spool speed, altitude thrust, ram drag, cruise SFC, throttle setting |
| propulsion/rocket/rocket-sizing | Rocket sizing | rocket equation delta-v, mass ratio, propellant mass, staging |
| propulsion/rocket/nozzle-design | Rocket nozzle design | area ratio, exit Mach, mass flow, ideal thrust, expansion |
| propulsion/rocket/propellant-selection | Propellant selection | propellant families, density impulse, mixture ratio, storability, mass fraction |
| propulsion/axial-compressor/axial-compressor-stage | Axial compressor stage | velocity triangle, specific work, flow coefficient, degree of reaction, stage pressure ratio, blade loading |
| propulsion/axial-compressor/compressor-map | Compressor map | surge line and margin, operating line, speed lines, corrected flow and speed, choke |
| propulsion/axial-compressor/multi-stage-compressor | Multi-stage compressor | overall pressure ratio, stage count, stage matching, reheat factor, annulus area, corrected speed |

## Routing guidance

- Brayton/gas-turbine thermodynamics route to the gas-turbine-cycle
  sub-skill; regenerator and recuperator cycle questions route to the
  regenerative-cycle sub-skill.
- Turbofan bypass and efficiency questions route to turbofan-cycle.
- Bypass-ratio design-trade questions (BPR vs TSFC, thrust split) route
  to the turbofan bypass-ratio-trade sub-skill.
- Rocket equation, delta-v, staging, and propellant mass questions
  route to the rocket-sizing sub-skill.
- Rocket nozzle questions (area ratio, exit Mach, thrust, expansion)
  route to the rocket nozzle-design sub-skill.
- Propellant family, density impulse, and mixture ratio questions route
  to the rocket propellant-selection sub-skill.
- Axial compressor stage questions (velocity triangles, degree of
  reaction, stage pressure ratio) route to the
  axial-compressor-stage sub-skill.
- Compressor map questions (surge margin, operating line, speed lines,
  corrected flow and speed) route to the compressor-map sub-skill.
- Multi-stage compressor questions (overall pressure ratio, stage
  count, stage matching, reheat factor, annulus area) route to the
  multi-stage-compressor sub-skill.
- Non-ideal cycle questions (component efficiencies, pressure loss,
  real SFC) route to the real-cycle-effects sub-skill.
- Off-design turbofan questions (corrected flow and speed, altitude
  thrust, ram drag, cruise SFC, throttle setting) route to the
  turbofan-off-design sub-skill.
- Airframe, stability, and certification questions route to their
  domain packs (flight-mechanics, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
