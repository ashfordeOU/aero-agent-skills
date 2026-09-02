---
name: regenerative-cycle
description: "Use when you must analyze a gas turbine cycle with regeneration: compute the regenerative Brayton cycle thermal efficiency from the pressure ratio, temperature limits, and regenerator effectiveness, estimate the optimum pressure ratio at which turbine exhaust heat recovery stops paying off, and quantify the efficiency gain over the simple cycle in percentage points. Produces the regenerative efficiency, the simple cycle efficiency for comparison, the optimum pressure ratio, and the gain, all in SI units, that gate the engine cycle assessment. Trigger: regenerative cycle, regenerator, recuperator, effectiveness, exhaust heat, optimum pressure ratio, thermal efficiency."
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
  tags: [regenerative-cycle, regenerator, recuperator, effectiveness, exhaust-heat, optimum-pressure-ratio, thermal-efficiency, brayton-cycle, turbine]
  version: 0.1.0
  author: Aero Agent Skills
---

# Regenerative Cycle (propulsion/gas-turbine-cycle)

Use when the task is a gas turbine (Brayton) cycle with
regeneration: a regenerator or recuperator recovers turbine
exhaust heat to preheat the compressor exit air, and you must
estimate the cycle efficiency, the optimum pressure ratio, or
the gain over the simple cycle.

## Domain quick reference

- A regenerator transfers heat from the turbine exhaust (state 4)
  to the compressor exit air (state 2), preheating it before the
  combustor. Effectiveness: eps = (T5 - T2)/(T4 - T2), where T5 is
  the preheated cold-side exit and T6 the cooled hot-side exit.
- Isentropic relations: T2 = T1 * PR**((gamma-1)/gamma) for the
  compressor and T4 = T3 / PR**((gamma-1)/gamma) for the turbine.
- Regenerative thermal efficiency:
  eta_reg = 1 - (T6 - T1)/(T3 - T5), with
  T5 = T2 + eps*(T4 - T2) and T6 = T4 - eps*(T4 - T2).
  At eps = 0 it collapses to the simple cycle.
- Simple cycle efficiency: eta = 1 - PR**((1-gamma)/gamma).
- Regeneration helps when the turbine exhaust is hotter than the
  compressor exit (T4 > T2, low pressure ratios) and hurts when
  T4 < T2 (high pressure ratios). The crossover, where the
  regenerator temperature difference vanishes, is the optimum
  pressure ratio: PR_opt = (T3/T1)**(gamma/(2*(gamma-1))).
- Efficiency gain in percentage points:
  gain = (eta_regenerative - eta_simple) * 100.
- Units: temperatures in kelvin, pressure ratio, effectiveness,
  and efficiency dimensionless, gain in percentage points.
- Air-standard values: gamma = 1.4, cp = 1005 J/(kg K).

## Workflow

1. Fix the pressure ratio, the temperature limits T1, T3, and the
   regenerator effectiveness eps (0 to 1).
2. Compute the simple cycle efficiency with simple_cycle_efficiency.
3. Compute the regenerative efficiency with regenerative_efficiency.
4. Compute the optimum pressure ratio with
   optimum_pressure_ratio_regenerative as the design boundary.
5. Compute the gain with efficiency_gain.
6. Report both efficiencies, the gain in points, and how the
   pressure ratio compares with PR_opt.

## Pitfalls

- Unit confusion: kelvin, never Celsius or Rankine, in the
  temperature relations.
- Passing effectiveness outside 0 to 1: non-physical, ValueError.
- Forgetting that eps = 0 must reproduce the simple cycle; use it
  as a sanity check.
- Quoting efficiency as a percent instead of a fraction; the gain
  is in percentage points, the efficiencies are fractions.
- Assuming regeneration always helps: above PR_opt it lowers
  efficiency because the exhaust is cooler than the compressor
  exit air.
- Using total pressure instead of the pressure ratio, or a
  pressure ratio at or below 1.
- Passing a turbine inlet temperature at or below the inlet
  temperature T1: ValueError.

## Behavior contract (gate 3)

The regenerative cycle logic is exercised by the gate 3 contract
test: scripts/test_regenerative_cycle.py against
scripts/regenerative_cycle_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_regenerative_cycle.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government
  work (public domain) and covers engine type certification, not
  cycle analysis methods; the regenerative Brayton relations are
  common-knowledge thermodynamics, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
