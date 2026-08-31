---
name: power-thermal-budget
description: "Use when sizing spacecraft electrical power and thermal budgets per ECSS practice: estimate battery capacity from eclipse power draw, depth of discharge, and efficiency; size the solar array from daylight-only generation; and check power margins against spacecraft bus requirements. The skill covers orbit-period eclipse fractions, battery sizing, solar array sizing, and margin checks for power budgets. Trigger: power budget, thermal budget, eps, eclipse, battery sizing, solar array, spacecraft, orbit period, power margin."
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
  tags: [power-budget, thermal-budget, eps, eclipse, battery-sizing, solar-array, spacecraft, orbit-period, power-margin]
  version: 0.1.0
  author: AeroSkills
---

# Spacecraft Power / Thermal Budget (space-systems/subsystems/power-thermal-budget)

Use when the task is spacecraft electrical power system (EPS)
budgeting: eclipse fraction from orbit geometry, battery sizing
against eclipse demand, solar array sizing for daylight-only
generation, and power margin checks.

## Domain quick reference

- Eclipse fraction: f = eclipse_min / orbit_period_min (0 < f < 1).
- Battery capacity required (Wh):
  C = power_w * (eclipse_min/60.0) / (dod * efficiency).
- Sizing margin: sized capacity must be >= required * (1 + margin);
  typical margin 0.20.
- Solar array power (daylight-only generation):
  P_sa = power_w / (efficiency * (1 - eclipse_fraction)) * (1 + margin).
- Power margin: margin = available/required - 1; typical minimum
  0.20. ECSS-E-ST-20C and ECSS-E-ST-10C set the European
  baseline for EPS and systems engineering budgets.

## Workflow

1. Determine the orbit period and worst-case eclipse duration;
   compute the eclipse fraction.
2. Size the battery from eclipse power draw, depth of discharge,
   and efficiency; apply the sizing margin.
3. Size the solar array from the day-side power demand and
   generation efficiency.
4. Check the power margin against the bus requirement.
5. Confirm the deterministic checks with the contract test
   scripts/test_power_thermal.py.

## Pitfalls

- Sizing the battery from average power instead of eclipse
  demand.
- Forgetting depth of discharge and efficiency losses in battery
  capacity.
- Assuming the array generates during eclipse.
- Zero or inverted eclipse fractions (eclipse longer than the
  orbit period).

## Behavior contract (gate 3)

The eclipse, battery, array, and margin logic is exercised by the
gate 3 contract test: scripts/test_power_thermal.py against
scripts/power_thermal_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_power_thermal.py

## Compliance

- Standards referenced, not reproduced: ECSS standards are freely
  downloadable (copyright ESA); summary-only per standards-map.yaml
  and brief 06.
- compliance: STANDARDS-REF, gated: false.
