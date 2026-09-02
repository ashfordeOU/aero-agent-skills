---
name: gas-turbine-cycle
description: "Use when you must compute the ideal gas turbine (Brayton) cycle: estimate the thermal efficiency, the compressor exit temperature, the turbine exit temperature, and the net specific work from the pressure ratio and the cycle temperature limits. Produces the cycle efficiency, station temperatures, and specific work in SI units that gate the engine cycle assessment. Trigger: gas turbine, brayton cycle, thermal efficiency, pressure ratio, compressor, turbine, engine cycle."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: gas-turbine-cycle
  tags: [gas-turbine, brayton-cycle, thermal-efficiency, compressor, turbine, pressure-ratio, engine-cycle]
  version: 0.1.0
  author: Aero Agent Skills
---

# Ideal Gas Turbine Cycle (propulsion/gas-turbine-cycle)

Use when the task is an ideal gas turbine (Brayton) cycle:
efficiency, compressor and turbine exit temperatures, and net
specific work from the pressure ratio and temperature limits.

## Domain quick reference

- The ideal Brayton cycle compresses isentropically, adds heat at
  constant pressure, expands isentropically, and rejects heat at
  constant pressure.
- Thermal efficiency depends only on the pressure ratio:
  eta = 1 - PR**((1-gamma)/gamma); it rises with pressure ratio.
- Isentropic temperature ratios: T2/T1 = PR**((gamma-1)/gamma) for
  the compressor and T4/T3 = PR**((1-gamma)/gamma) for the turbine.
- Net specific work: w = cp*(T3 - T2) - cp*(T2 - T1) with the
  compressor exit temperature T2 from the isentropic relation.
- Units: temperatures in kelvin, pressure ratio dimensionless,
  gamma dimensionless, cp in J/(kg K), specific work in J/kg.
- Air-standard values: gamma = 1.4, cp = 1005 J/(kg K).

## Workflow

1. Fix the pressure ratio and the temperature limits T1, T3.
2. Compute the efficiency with brayton_thermal_efficiency.
3. Compute T2 with compressor_exit_temperature.
4. Compute T4 with turbine_exit_temperature.
5. Compute the net specific work with cycle_specific_work.
6. Report efficiency, station temperatures, and specific work.

## Pitfalls

- Unit confusion: kelvin, never Celsius or Rankine, in the
  temperature relations.
- Using total pressure instead of the pressure ratio: PR is the
  dimensionless ratio, not a pressure value.
- Passing a pressure ratio of 1 or below, or temperatures at or
  below zero: the functions raise ValueError.
- Quoting efficiency as a percent instead of a fraction.
- Assuming gamma and cp stay constant across real components;
  these are ideal-cycle values.

## Behavior contract (gate 3)

The efficiency, temperature, and work logic is exercised by the
gate 3 contract test: scripts/test_gas_turbine_cycle.py against
scripts/gas_turbine_cycle_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_gas_turbine_cycle.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government
  work (public domain) and covers engine type certification, not
  cycle analysis methods; the ideal Brayton relations are
  common-knowledge thermodynamics, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
