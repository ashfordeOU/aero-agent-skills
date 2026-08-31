---
name: propulsion
description: "Use when a task concerns aircraft or rocket propulsion: guide the router to the propulsion pack, whose gas-turbine-cycle sub-skill covers ideal Brayton cycle analysis, turbofan-cycle covers bypass ratio and propulsive efficiency parameters, bypass-ratio-trade covers the bypass ratio design trade with thrust split, rocket-sizing covers the rocket equation, mass ratio, and staging delta-v, nozzle-design covers rocket nozzle area ratio, exit Mach, and ideal thrust, and axial-compressor-stage covers the single axial compressor stage velocity triangle with specific work, degree of reaction, and stage pressure ratio. This pack is the propulsion performance and sizing layer of the library. Trigger: propulsion, gas turbine, Brayton cycle, turbofan, bypass ratio, rocket equation, delta-v, rocket nozzle, area ratio, exit Mach, axial compressor, compressor stage, velocity triangle, degree of reaction, blade loading."
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
performance parameters, rocket sizing, rocket nozzles, or axial
compressor stages.

## Domain

Propulsion: gas turbine and turbofan thermodynamic cycle analysis,
turbofan bypass design trades, launch-vehicle rocket sizing with the
rocket equation and staging, rocket nozzle design, and axial
compressor stage analysis.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| propulsion/gas-turbine-cycle/gas-turbine-cycle | Gas turbine cycle | Brayton thermal efficiency, compressor/turbine exit temperatures, pressure ratio |
| propulsion/turbofan/turbofan-cycle | Turbofan cycle | bypass ratio, propulsive efficiency, specific thrust, fan/core mass flow |
| propulsion/turbofan/bypass-ratio-trade | Bypass ratio trade | BPR vs TSFC, thrust split, specific thrust, fan pressure ratio |
| propulsion/rocket/rocket-sizing | Rocket sizing | rocket equation delta-v, mass ratio, propellant mass, staging |
| propulsion/rocket/nozzle-design | Rocket nozzle design | area ratio, exit Mach, mass flow, ideal thrust, expansion |
| propulsion/axial-compressor/axial-compressor-stage | Axial compressor stage | velocity triangle, specific work, flow coefficient, degree of reaction, stage pressure ratio, blade loading |

## Routing guidance

- Brayton/gas-turbine thermodynamics route to the gas-turbine-cycle
  sub-skill; turbofan bypass and efficiency questions route to
  turbofan-cycle.
- Bypass-ratio design-trade questions (BPR vs TSFC, thrust split) route
  to the turbofan bypass-ratio-trade sub-skill.
- Rocket equation, delta-v, staging, and propellant mass questions
  route to the rocket-sizing sub-skill.
- Rocket nozzle questions (area ratio, exit Mach, thrust, expansion)
  route to the rocket nozzle-design sub-skill.
- Axial compressor stage questions (velocity triangles, degree of
  reaction, stage pressure ratio) route to the
  axial-compressor-stage sub-skill.
- Airframe, stability, and certification questions route to their
  domain packs (flight-mechanics, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
