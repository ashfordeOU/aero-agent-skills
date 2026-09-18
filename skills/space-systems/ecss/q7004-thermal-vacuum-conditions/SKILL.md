---
name: q7004-thermal-vacuum-conditions
description: "Define the thermal vacuum conditions a run has to hold: pressure, temperature limits and dwell. Use when the ECSS-Q-ST-70-04C condition clauses have to be checked against a real chamber before a thermal vacuum run: show the pressure is low enough by putting the mean free path against the item, refuse a cold limit the shroud cannot reach, build each dwell from the item's lag plus its outgassing soak, guard both ends of the run with the dew point, and order pump-down before cooling and warm-up before gas. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-vacuum-chamber-pressure, free-molecular-knudsen-check, shroud-limited-cold-temperature, vacuum-outgassing-dwell, repressurization-dew-point-guard."
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
  subdomain: ecss
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-thermal-vacuum-conditions, thermal-vacuum-chamber-pressure, free-molecular-knudsen-check, shroud-limited-cold-temperature, vacuum-outgassing-dwell, repressurization-dew-point-guard]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Thermal Vacuum Conditions (space-systems/ecss/q7004-thermal-vacuum-conditions)

Use when the task is the thermal vacuum conditions of ECSS-Q-ST-70-04C —
settling the pressure the chamber has to hold, the temperature limits it can
actually reach, the dwell at each of them, and the order the run is carried
out in so neither end condenses moisture onto the item.

## Domain quick reference

- The pressure requirement is not a number to be met once at the start. It is
  a condition to be held for the whole run, because the point of the vacuum
  is to remove the gas as a heat transfer path, and a chamber that drifts
  upward mid-run quietly restores it.
- The check that shows the gas is gone is the mean free path against the
  item, not the gauge reading alone. Once molecules travel further between
  collisions than the distance the heat has to cross, the gas no longer
  carries heat and the item exchanges by radiation and conduction, which is
  the flight condition. A large item at a given pressure is further from that
  condition than a small one, so the item's size belongs in the check.
- The shroud is the cold sink and the chamber cannot drive the item below it.
  A cold limit set under the shroud temperature is not a demanding
  requirement, it is an unachievable one, and it has to be restated rather
  than chased with a longer dwell.
- The vacuum dwell carries two jobs at once: waiting for the item's lag to
  decay inside the tolerance band, and holding long enough for the outgassing
  to settle. The dwell is their sum, floored by the declared minimum, and
  which of the three set it is worth reporting.
- Both ends of the run are dew-point guarded. Cooling before the chamber has
  pumped down condenses residual vapor onto the cold item; admitting gas onto
  a cold item at the end does the same. The guard is the dew point plus a
  declared margin, and the item has to be above it before a valve opens.
- The item temperature and the chamber pressure at the moment of
  repressurization are part of the record, because a condensation event
  afterwards cannot be reconstructed from the profile alone.

## Workflow

1. Declare the two temperature limits, the chamber base pressure, the
   characteristic length of the item, the shroud temperature and the dew
   point. Reject inverted limits rather than sorting them silently.
2. Assess the pressure twice: against the declared test pressure, and against
   the free-molecular threshold using the mean free path over the item's
   characteristic length. Both have to hold.
3. Check the cold limit against the shroud and report the achievable limit
   where the requested one is out of reach.
4. Build the hot and cold dwells from the item's time constant, the
   stabilization tolerance and the outgassing soak declared for each end.
5. Compute the dew-point guard and check the planned repressurization
   temperature against it.
6. Emit the ordered sequence — pump, then cool; warm, then admit gas — and
   close with the acceptability verdict, the findings and the duty to hold
   the pressure for the whole run.

## Pitfalls

- Reading the pressure once at the start of the run. The requirement covers
  the whole profile, and outgassing at the hot dwell is exactly when the
  chamber is most likely to drift above it.
- Judging the vacuum on the gauge alone for a large item. The same pressure
  that is free-molecular across a small coupon still carries heat across a
  meter-scale structure, so the item's size has to enter the check.
- Cooling while the chamber is still pumping. The cold item becomes the
  coldest surface available and collects whatever vapor is left, which
  changes its mass, its surfaces and sometimes its function.
- Admitting gas onto a cold item at the end of the run. The condensation
  happens outside the profile, so the data looks clean and the item is wet.
- Setting the cold limit from the mission alone. If it sits below the shroud
  the chamber cannot reach it, and the run silently qualifies to the shroud
  temperature while the report claims the requested one.
- Treating the vacuum dwell as the cycling dwell. Without convection the lag
  decays more slowly, and the outgassing soak is an additional requirement,
  not an alternative to stabilization.

## Behavior contract (gate 3)

The mean free path and Knudsen check, pressure assessment, shroud-limited
cold limit, vacuum dwell construction, dew-point guard, run sequence and the
acceptability verdict are exercised by the gate 3 contract test:
scripts/test_q7004_thermal_vacuum_conditions.py against
scripts/q7004_thermal_vacuum_conditions_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_thermal_vacuum_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
