---
name: propulsion
description: "Use when a task concerns aircraft or rocket propulsion: guide the router to the propulsion pack, whose gas-turbine-cycle sub-skill covers ideal Brayton cycle analysis (thermal efficiency, compressor and turbine exit temperatures), turbofan-cycle covers bypass ratio and propulsive efficiency parameters, and rocket-sizing covers the rocket equation, mass ratio, propellant mass, and staging delta-v. This pack is the propulsion performance and sizing layer of the library. Trigger: propulsion, gas turbine, Brayton cycle, turbofan, bypass ratio, rocket equation, delta-v, specific impulse, engine cycle."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
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
performance parameters, or rocket sizing.

## Domain

Propulsion: gas turbine and turbofan thermodynamic cycle analysis,
and launch-vehicle rocket sizing with the rocket equation and
staging.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| propulsion/gas-turbine-cycle/gas-turbine-cycle | Gas turbine cycle | Brayton thermal efficiency, compressor/turbine exit temperatures, pressure ratio |
| propulsion/turbofan/turbofan-cycle |
| propulsion/turbofan/bypass-ratio-trade | Bypass ratio trade | BPR vs TSFC, thrust split, specific thrust, fan pressure ratio | Turbofan cycle | bypass ratio, propulsive efficiency, specific thrust, fan/core mass flow |
| propulsion/rocket/rocket-sizing |
| propulsion/rocket/nozzle-design | Rocket nozzle design | area ratio, exit Mach, mass flow, ideal thrust, expansion | Rocket sizing | rocket equation delta-v, mass ratio, propellant mass, staging |

## Routing guidance

- Brayton/gas-turbine thermodynamics route to the gas-turbine-cycle
  sub-skill; turbofan bypass and efficiency questions route to
  turbofan-cycle.
- Rocket equation, delta-v, staging, and propellant mass questions
  route to the rocket-sizing sub-skill.
- Rocket nozzle questions (area ratio, exit Mach, thrust, expansion)
  route to the rocket nozzle-design sub-skill.
- Bypass-ratio design-trade questions (BPR vs TSFC, thrust split) route
  to the turbofan bypass-ratio-trade sub-skill.
- Airframe, stability, and certification questions route to their
  domain packs (flight-mechanics, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
