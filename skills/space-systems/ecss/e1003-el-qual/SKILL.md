---
name: e1003-el-qual
description: "Use when define the element qualification test baseline for a space hardware item under ECSS-E-ST-10C §6.2: determine the qualification approach (full qualification versus protoflight) from the element category and prototype test history, map the mission environment drivers to the required test types, compute the qualification level by applying the standard margin over the acceptance level for each test type (vibration, acoustic, shock, thermal cycling, thermal vacuum, quasi-static), compute the qualification duration by applying the duration factor or soak extension over the acceptance duration, and verify that a proposed test plan meets every level and duration requirement against the computed baseline. Trigger: ecss, e-st-10c, element-qualification, qualification-level, qualification-duration, test-baseline, vibration-margin, thermal-margin, protoflight, acceptance-level."
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
  tags: [ecss, e-st-10c, element-qualification, qualification-level, qualification-duration, test-baseline, vibration-margin, thermal-margin, protoflight]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Environmental Testing — Element Qualification Test Baseline (space-systems/ecss/e1003-el-qual)

Use when the task is to define the qualification test baseline for a space
hardware element under ECSS-E-ST-10C §6.2 — establishing which test types
apply, what qualification levels must be reached (acceptance level plus
margin), and what qualification durations must be met (acceptance duration
multiplied by factor or extended by soak allowance), and verifying that a
proposed test plan satisfies every requirement.

## Domain quick reference

- §6.2 + Tables 6-1/6-2 govern two linked topics: the qualification level
  (the environmental stress level that demonstrates adequate design margin
  above the acceptance level) and the qualification duration (the test
  exposure time that exercises the item beyond acceptance without
  overstressing). Both must be met; passing one does not excuse the other.
- **Qualification approach**: a hardware item follows one of two routes.
  *Full qualification* applies when a dedicated prototype model has completed
  the full qualification test sequence before the flight article is built —
  the flight article then undergoes acceptance testing only. *Protoflight*
  applies when a single article must serve as both the qualification unit and
  the flight unit — it is exposed to qualification levels but acceptance
  durations to preserve flight service life.
- **Level margins** (paraphrased from Table 6-1): for vibration (sine and
  random), acoustic, and shock, the qualification level is the acceptance
  level plus 3 dB. For thermal tests (cycling and vacuum), the qualification
  temperature boundary is the acceptance boundary extended by 10 °C on each
  side. For quasi-static loading, the qualification load is 1.5 times the
  acceptance load.
- **Duration factors** (paraphrased from Table 6-2): sine vibration and
  acoustic are run for 2× the acceptance duration; random vibration for 4×
  (minimum 120 s per axis regardless); thermal cycling for 2× the acceptance
  cycle count; thermal vacuum for the acceptance soak duration plus 2 hours
  per thermal level. Shock testing requires a minimum of 3 shots per axis.
  Quasi-static tests use the same duration as acceptance — the margin is in
  the load, not the time.
- **Protoflight floor**: even in protoflight the minimum duration floors
  apply (120 s random vibration, 3 shots shock). Protoflight duration
  factors revert to 1× for all other test types.

## Workflow

1. Determine the qualification approach: check whether a dedicated prototype
   model has completed the full qualification test sequence. If yes, assign
   *full_qualification*; if the article must serve as both the qualification
   and flight unit, assign *protoflight*. A protoflight-model article is
   always protoflight. Reject breadboard items — they do not carry a flight
   qualification category.
2. Map the mission environment drivers (launch vibration, launch acoustic,
   launch shock, on-orbit thermal, pyrotechnic shock) to the minimum required
   test types per §6.2. Report any unrecognized driver as an error before
   proceeding.
3. For each required test type, compute the qualification level: acceptance
   level + 3 dB for vibration and shock types; acceptance boundary ± 10 °C
   for thermal types; acceptance load × 1.5 for quasi-static. Record the
   margin applied and the unit.
4. For each required test type, compute the qualification duration using the
   qualification approach determined in step 1: apply the duration factor for
   full qualification (2× for sine/acoustic, 4× for random, 2× cycle count
   for thermal cycling, acceptance soak + 2 h for thermal vacuum); hold
   acceptance duration for protoflight. Enforce floor minimums in all cases
   (120 s per axis for random vibration, 3 shots per axis for shock).
5. Build the qualification test baseline: each test type, its required
   qualification level, and its required qualification duration. Flag any
   test type present in the baseline that lacks a corresponding entry in the
   proposed test plan.
6. Validate the proposed test plan against the baseline: for each test type,
   check that the proposed level meets or exceeds the required qualification
   level and that the proposed duration meets or exceeds the required
   qualification duration. Collect all shortfalls as findings; empty findings
   list = compliant plan.

## Pitfalls

- Using acceptance levels as qualification levels without applying the dB
  or thermal margins — the qualification baseline is defined by the margin
  table, not by the acceptance specification.
- Applying duration factors in protoflight — protoflight intentionally uses
  acceptance durations to protect the flight article; applying a 2× or 4×
  factor in protoflight is an error that over-stresses the item.
- Ignoring minimum duration floors in protoflight — the floors (120 s random
  vibration, 3 shots shock) are mandatory regardless of qualification
  approach; they are not duration factors and still apply when the factor
  is 1×.
- Treating a missing qualification level or duration for one test type as a
  pass because other tests are compliant — the baseline is per-test-type;
  non-compliance in any single test type is a finding.
- Setting the thermal qualification boundary only on the hot side and
  omitting the cold side — Table 6-1 extends the boundary in both directions;
  both extremes must be verified.

## Behavior contract (gate 3)

The qualification-approach determination, environment-to-test mapping,
level-margin computation, duration-factor computation, floor enforcement,
and test-plan validation logic are exercised by the gate 3 contract test:
scripts/test_e1003_el_qual.py against scripts/e1003_el_qual_logic.py
(stdlib unittest, offline). Run:

    python3 scripts/test_e1003_el_qual.py

## Compliance

- ECSS standards are freely downloadable from ESA. Cite clause and table
  as the anchor only; all procedure text is paraphrased.
- compliance: STANDARDS-REF, gated: false.
- Anchor: ECSS-E-ST-10C §6.2, Table 6-1 (qualification levels),
  Table 6-2 (qualification durations).
