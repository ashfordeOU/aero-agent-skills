---
name: thermal-design
description: "Use when you must size the thermal control subsystem for a spacecraft: compute the radiator area from the Stefan-Boltzmann balance, solve the equilibrium radiator temperature for a heat load, and check the thermal margin against the dissipation budget. Produces the radiator sizing, the equilibrium temperature, and the margin verdict that gate the thermal design. Trigger: thermal design, radiator sizing, thermal balance, heat load, spacecraft thermal control."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: subsystems
  tags: [thermal-design, radiator-sizing, thermal-balance, heat-load, spacecraft-thermal-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# Spacecraft Thermal Design (space-systems/subsystems/thermal-design)

Use when the task is spacecraft thermal control design: radiator
sizing, equilibrium temperature, and thermal margin checks against
the dissipation budget.

## Domain quick reference

- A radiator dissipates heat to the environment by radiation:
  Q = eps * sigma * A * (T_rad^4 - T_sink^4).
- The radiator must run hotter than the sink it radiates to, or the
  balance is physically wrong.
- Equilibrium temperature follows from the same balance solved for
  temperature.
- Thermal margin is the dissipation capacity beyond the required
  load; typical project bands require 10-20 percent.

## Workflow

1. Collect the heat load, radiator temperature, sink temperature,
   and surface emissivity.
2. Size the radiator with radiator_area.
3. Solve the equilibrium temperature with equilibrium_temp.
4. Check the margin with thermal_margin_ok.
5. Gate the thermal design on the margin verdict.

## Pitfalls

- Sizing a radiator colder than its sink (negative net flow).
- Ignoring emissivity degradation over life.
- Treating absorbed heat as dissipated heat.

## Behavior contract (gate 3)

The radiator, equilibrium, and margin logic is exercised by the gate
3 contract test: scripts/test_thermal_design.py against
scripts/thermal_design_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_thermal_design.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-31 text is
  copyright ESA; the sizing here is common thermal physics,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
