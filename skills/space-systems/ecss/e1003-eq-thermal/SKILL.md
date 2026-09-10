---
name: e1003-eq-thermal
description: "Use when running equipment-level thermal tests under ECSS-E-ST-10-03C clause 5.5.4: select thermal vacuum vs thermal test at mission pressure for a unit based on its vacuum exposure, execute the qualification/acceptance/protoflight thermal cycle plan (cold/hot plateaus, dwell stabilization, functional/performance checks at the extremes), and verify the test as complete only when every required cycle stabilizes and passes. Trigger: thermal vacuum, TVAC, thermal cycling, thermal test at mission pressure, equipment thermal test, dwell stabilization, hot plateau, cold plateau, e-st-10-03, ecss."
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
  tags: [ecss, e-st-10-03c, thermal-vacuum, thermal-cycling, equipment-test, tvac]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment Thermal Tests (space-systems/ecss/e1003-eq-thermal)

Use when the task is running equipment-level thermal testing under
ECSS-E-ST-10-03C clause 5.5.4: choosing between thermal vacuum and
thermal test at mission pressure, executing the qualification/
acceptance/protoflight thermal cycle plan, and verifying the test is
actually complete.

## Domain quick reference

- ECSS-E-ST-10-03C clause 5.5.4 covers the two equipment-level thermal
  test types: thermal vacuum (the unit is exposed to vacuum in its
  operational environment) and thermal test at mission pressure (the
  unit operates sealed or pressurized and is not vacuum-exposed).
- The temperature levels and the cycle-count/duration baselines for
  each test campaign (qualification, acceptance, protoflight) are set
  by the sibling baseline leaves (e1003-eq-qual Table 5-1/5-2,
  e1003-eq-acceptance Table 5-3/5-4, e1003-eq-protoflight Table
  5-5/5-6); this leaf consumes those levels and carries the per-test
  rules: cycling execution, plateau stabilization tolerance, and
  functional/performance success criteria.
- A thermal cycle has a cold plateau and a hot plateau. A plateau is
  stable only once the temperature holds inside tolerance of its
  target for the whole commanded dwell window, not merely at the
  instant it first touches the target.
- Functional/performance verification is mandatory at the temperature
  extremes of the first and last cycle at minimum, in addition to any
  ambient checks before and after the test; a plateau without the
  required functional/performance result cannot be certified even if
  it stabilized thermally.

## Workflow

1. Determine whether the unit is vacuum-exposed in its operational
   environment; select thermal_vacuum if so, otherwise
   thermal_at_mission_pressure.
2. Pull the hot/cold temperature targets, tolerance, dwell duration,
   and required cycle count for the applicable campaign
   (qualification/acceptance/protoflight) from the matching sibling
   baseline leaf.
3. Build the cycle plan from those levels: the required number of
   cold/hot plateau pairs, each held for the commanded dwell.
4. Record temperature readings through each plateau; a plateau counts
   as stable only when a contiguous run covering the full dwell window
   stays within tolerance of the target.
5. At the first and last cycle's plateaus (minimum), execute and
   record the functional/performance test; treat a required plateau
   with no functional result as unresolved regardless of its thermal
   stabilization.
6. Declare the thermal test complete only when: the executed test type
   matches the unit's vacuum exposure, the executed cycle count meets
   the plan's required count, every plateau stabilized, and every
   required functional/performance check passed.

## Pitfalls

- Running a thermal test at mission pressure on a unit that is
  actually vacuum-exposed in operation, or vice versa.
- Treating the first instant the target temperature is touched as the
  plateau being achieved, instead of requiring stability through the
  whole dwell window.
- Skipping the functional/performance test at the first or last
  cycle's extremes and still certifying the cycle or the test.
- Declaring the test complete with fewer cycles than the campaign's
  baseline plan requires.

## Behavior contract (gate 3)

The test-type selection, cycle-plan construction, plateau-stabilization,
and completion logic is exercised by the gate 3 contract test:
scripts/test_e1003_eq_thermal.py against
scripts/e1003_eq_thermal_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_thermal.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
