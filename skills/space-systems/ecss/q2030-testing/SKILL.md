---
name: q2030-testing
description: "Audit the test programme of a manufactured electrical harness under ECSS-Q-ST-20-30C section 6.19 and its IPC section 19 acceptance basis. Use when the task is deciding which tests a harness owes and whether the recorded results support acceptance: nondestructive examination, continuity graded against a loop resistance computed from conductor length, cross-section and mated contact count, insulation resistance at its electrification time, a dielectric withstanding voltage derived from the working voltage, pull strength scaled to conductor size, and the reduced-level retest a reworked harness owes. Trigger: ecss, q-st-20-30c, harness-continuity-test, harness-insulation-resistance, harness-dielectric-withstanding-test, harness-pull-test, harness-test-after-rework, ipc-whma-a-620-harness-testing."
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
  tags: [ecss, q-st-20-30-harness-scope, q2030-testing, harness-continuity-test, harness-insulation-resistance, harness-dielectric-withstanding-test, harness-pull-test, harness-test-after-rework]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Harness Testing (space-systems/ecss/q2030-testing)

Use when the task is the harness testing provision of ECSS-Q-ST-20-30C
section 6.19, which binds the testing section of the IPC/WHMA-A-620
acceptance basis — deciding which tests a finished harness owes, what
the pass criteria for each of them are, and what a reworked or
repaired harness has to repeat before it is accepted again.

## Domain quick reference

- The owed test set follows from the build, not from habit.
  Nondestructive examination and electrical continuity are owed by
  every harness. Insulation resistance is owed once there is something
  to isolate — more than one conductor, or a shield. A dielectric
  withstanding voltage test is owed once the working voltage is above
  the low-voltage threshold; below it the insulation is not being
  asked to hold anything and the test only stresses it.
- Continuity has a computable expectation. The loop resistance of a
  harness leg is the conductor resistance of its length and
  cross-section plus an allowance for each mated contact pair in the
  path. Grading against that expectation widened by the build tolerance
  catches a partially engaged contact that a generous fixed limit lets
  through.
- An insulation-resistance reading is time-dependent. The current
  through the dielectric is still falling while the sample polarises,
  so a reading taken before the electrification time has elapsed is
  optimistic and is not admissible whatever number it shows.
- The dielectric withstanding voltage is derived from the working
  voltage, not chosen. Applying less than the derived level does not
  demonstrate the margin; applying more than it after a harness has
  already been proved once stresses insulation that has no remaining
  purpose, which is why a retest is run at a reduced level.
- Rework and repair reopen the test programme. Every rework repeats the
  examination and the continuity check, and a rework that touched
  insulation or a shield reopens the isolation tests too — at the
  reduced dielectric level, so the insulation is not taken to full
  proof twice.

## Workflow

1. Validate the harness record: identifier, conductor count, mated
   contact pairs, length, cross-section, shield flag, working voltage
   and the recorded results. A non-positive length or cross-section, a
   conductor count below one, or a result under an unknown test name is
   an input error, not a case to clamp.
2. Derive the owed test set from the build and return it in run order.
3. Compute the expected loop resistance and its limit, then grade the
   continuity reading against that limit.
4. Grade the insulation resistance against its floor and the reading
   against its electrification time.
5. Derive the dielectric withstanding voltage from the working voltage
   — reduced when the harness has been reworked — then grade the
   applied voltage, the dwell and the leakage current.
6. Scale the pull force to the conductor cross-section, with a floor
   for fine gauges, and grade the mechanical result where one is owed.
7. Name the owed tests with no result on record, list what a reworked
   harness repeats, and aggregate the lot, absorbing representation
   error at each limit with a named tolerance rather than by widening
   the limit.

## Pitfalls

- Grading continuity against a single fixed milliohm figure for every
  leg. Length, cross-section and contact count all move the
  expectation, and a fixed figure generous enough for the longest leg
  passes a defective short one.
- Accepting an insulation reading taken as soon as the voltage is
  applied. The value is still falling, so an early reading reports a
  resistance the harness does not have.
- Letting the applied dielectric voltage stand in for the required one.
  The required level comes from the working voltage, and a test run
  below it demonstrates nothing about the margin that was specified.
- Repeating the full-level dielectric test after every rework. Proof
  stress accumulates in the insulation; the repeat is run at the
  reduced level for that reason, and running it at full level is a
  finding rather than extra rigour.
- Closing a harness with an owed test simply absent. A missing result
  is not a pass, and it has to be named as missing rather than dropped
  from the owed set.

## Behavior contract (gate 3)

The harness validation, owed-test derivation, loop-resistance
computation and continuity limit, insulation-resistance and
electrification checks, dielectric voltage derivation with its reduced
retest level, scaled pull force, rework repeat set and lot aggregation
are exercised by the gate 3 contract test:
scripts/test_q2030_testing.py against scripts/q2030_testing_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q2030_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
